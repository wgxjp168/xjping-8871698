'use strict';

const sessionStore = require('./sessionStore');
const intentClient = require('./intentClient');
const decisionClient = require('./decisionClient');
const logger = require('./logger');
const {
  DialogState,
  createSession,
  appendMessage,
  mergeContext,
  transitionState,
} = require('../models/dialog');

// ─── Constants ────────────────────────────────────────────────────────────────

/**
 * Minimum number of entities / product params required before moving to
 * BRAND_DETECTION.  Adjust per product requirements.
 */
const MIN_ENTITIES_FOR_BRAND_DETECTION = 1;

/**
 * Minimum product parameters collected before triggering DECISION flow.
 */
const MIN_PARAMS_FOR_DECISION = 2;

// ─── Prompts / suggestions ────────────────────────────────────────────────────

const SUGGESTIONS_BY_STATE = {
  [DialogState.COLLECTING]: [
    'Tell me the product category you are looking for',
    'What is your approximate budget?',
    'Do you have a preferred brand?',
  ],
  [DialogState.BRAND_DETECTION]: [
    'Confirm the brand you have in mind',
    'Would you like to explore alternative brands?',
  ],
  [DialogState.DECISION]: [
    'Generating recommendations…',
  ],
  [DialogState.COMPLETED]: [
    'Start a new search',
    'Refine the current recommendation',
  ],
  [DialogState.ERROR]: [
    'Please try rephrasing your request',
    'Start a new session',
  ],
};

// ─── DialogManager class ──────────────────────────────────────────────────────

class DialogManager {
  /**
   * Starts a new dialog session.
   *
   * @param {string} userId
   * @param {string} initialMessage - First user utterance.
   * @returns {Promise<{ sessionId: string, message: string, state: string, suggestions: string[] }>}
   */
  async startSession(userId, initialMessage) {
    let session = createSession(userId);
    session = transitionState(session, DialogState.COLLECTING);
    session = appendMessage(session, 'user', initialMessage);

    await sessionStore.create(session.sessionId, session);
    logger.info({ msg: 'Dialog session started', sessionId: session.sessionId, userId });

    // Kick off first intent pass immediately so the very first response is informed.
    let intentResult = null;
    try {
      intentResult = await intentClient.recognize(initialMessage, session.context);
    } catch (err) {
      logger.warn({ msg: 'Intent recognition failed on session start', error: err.message });
    }

    if (intentResult) {
      session = mergeContext(session, { intent: intentResult.intent });
    }

    const response = this._buildResponse(session, intentResult);
    session = appendMessage(session, 'assistant', response.message);
    await sessionStore.update(session.sessionId, session);

    return response;
  }

  /**
   * Processes an incoming user message for an existing session.
   *
   * State machine flow:
   *   COLLECTING → (enough entities) → BRAND_DETECTION
   *   BRAND_DETECTION → (brand confirmed) → DECISION
   *   DECISION → (decision-svc called) → COMPLETED
   *
   * @param {string} sessionId
   * @param {string} userMessage
   * @returns {Promise<Object>} buildResponse output.
   */
  async processMessage(sessionId, userMessage) {
    let session = await sessionStore.get(sessionId);
    if (!session) {
      const err = new Error('Session not found');
      err.status = 404;
      throw err;
    }

    if (session.state === DialogState.COMPLETED || session.state === DialogState.ERROR) {
      return this._buildResponse(session, null, 'This session has already ended. Please start a new session.');
    }

    // 1. Append user message
    session = appendMessage(session, 'user', userMessage);

    // 2. Recognise intent
    let intentResult = null;
    try {
      intentResult = await intentClient.recognize(userMessage, session.context);
      session = mergeContext(session, { intent: intentResult.intent });
    } catch (err) {
      logger.error({ msg: 'Intent recognition failed', sessionId, error: err.message });
    }

    // 3. Extract entities
    let entityResult = null;
    try {
      entityResult = await intentClient.extractEntities(userMessage);
      if (entityResult?.entities?.length) {
        const merged = [...(session.context.entities || []), ...entityResult.entities];
        // Deduplicate by type+value
        const seen = new Set();
        const deduped = merged.filter((e) => {
          const id = `${e.type}:${e.value}`;
          if (seen.has(id)) return false;
          seen.add(id);
          return true;
        });
        session = mergeContext(session, { entities: deduped });
      }
    } catch (err) {
      logger.warn({ msg: 'Entity extraction failed', sessionId, error: err.message });
    }

    // 4. Accumulate product params from entities
    if (entityResult?.entities?.length) {
      const params = { ...session.context.productParams };
      for (const entity of entityResult.entities) {
        params[entity.type] = entity.value;
      }
      session = mergeContext(session, { productParams: params });
    }

    // 5. State machine transitions
    session = await this._advanceState(session);

    // 6. Persist updated session
    await sessionStore.update(session.sessionId, session);

    // 7. Build and persist assistant response
    const response = this._buildResponse(session, intentResult);
    session = appendMessage(session, 'assistant', response.message);
    await sessionStore.update(session.sessionId, session);

    return response;
  }

  /**
   * Advances the state machine based on the accumulated context.
   *
   * @private
   * @param {Object} session
   * @returns {Promise<Object>} Potentially mutated session.
   */
  async _advanceState(session) {
    const { state, context } = session;
    const entityCount = (context.entities || []).length;
    const paramCount = Object.keys(context.productParams || {}).length;

    if (state === DialogState.COLLECTING) {
      if (entityCount >= MIN_ENTITIES_FOR_BRAND_DETECTION) {
        session = transitionState(session, DialogState.BRAND_DETECTION);
        // Attempt brand detection
        try {
          const brandResult = await intentClient.detectBrand(
            context.intent || '',
            context.entities
          );
          session = mergeContext(session, { brandStatus: brandResult });
        } catch (err) {
          logger.warn({ msg: 'Brand detection failed', error: err.message });
        }
      }
    }

    if (session.state === DialogState.BRAND_DETECTION) {
      if (paramCount >= MIN_PARAMS_FOR_DECISION) {
        session = transitionState(session, DialogState.DECISION);
      }
    }

    if (session.state === DialogState.DECISION) {
      session = await this._triggerDecisionFlow(session);
    }

    return session;
  }

  /**
   * Triggers the AI Decision 8-step flow via decision-svc.
   *
   * @private
   * @param {Object} session
   * @returns {Promise<Object>} Session updated with decision result; state set to COMPLETED or ERROR.
   */
  async _triggerDecisionFlow(session) {
    try {
      logger.info({ msg: 'Triggering decision flow', sessionId: session.sessionId });

      const decisionPayload = {
        sessionId: session.sessionId,
        userId: session.userId,
        intent: session.context.intent,
        entities: session.context.entities,
        brandStatus: session.context.brandStatus,
        productParams: session.context.productParams,
        messages: session.messages,
      };

      const decisionResult = await decisionClient.analyze(decisionPayload);

      session = mergeContext(session, { decisionResult });
      session = transitionState(session, DialogState.COMPLETED);

      logger.info({
        msg: 'Decision flow completed',
        sessionId: session.sessionId,
        decisionId: decisionResult?.decisionId,
      });
    } catch (err) {
      logger.error({
        msg: 'Decision flow failed',
        sessionId: session.sessionId,
        error: err.message,
      });
      session = transitionState(session, DialogState.ERROR);
      session = mergeContext(session, { errorMessage: err.message });
    }

    return session;
  }

  /**
   * Constructs the response payload returned to the caller.
   *
   * @param {Object} session
   * @param {Object|null} intentResult
   * @param {string} [overrideMessage]
   * @returns {{ sessionId, message, state, suggestions, requiresMoreInfo }}
   */
  _buildResponse(session, intentResult, overrideMessage) {
    const { state, context } = session;
    let message = overrideMessage;
    let requiresMoreInfo = false;

    if (!message) {
      switch (state) {
        case DialogState.COLLECTING:
          requiresMoreInfo = true;
          message = this._collectingMessage(context, intentResult);
          break;

        case DialogState.BRAND_DETECTION:
          requiresMoreInfo = true;
          message = context.brandStatus?.brands?.length
            ? `I detected the following brands: ${context.brandStatus.brands.join(', ')}. Would you like to proceed with one of these, or explore alternatives?`
            : 'I\'m gathering information about brands relevant to your request. Could you specify a preferred brand?';
          break;

        case DialogState.DECISION:
          requiresMoreInfo = false;
          message = 'I have enough information to analyse your request. Running the AI decision flow now, please wait…';
          break;

        case DialogState.COMPLETED: {
          const decisionId = context.decisionResult?.decisionId;
          message = decisionId
            ? `Analysis complete! Your decision report ID is ${decisionId}. Here is the summary: ${context.decisionResult?.summary || 'Please check your report.'}`
            : 'Your session has been completed. Would you like to start a new search?';
          break;
        }

        case DialogState.ERROR:
          message = `An error occurred while processing your request: ${context.errorMessage || 'Unknown error'}. Please try again.`;
          break;

        default:
          message = 'How can I assist you today?';
      }
    }

    return {
      sessionId: session.sessionId,
      message,
      state,
      suggestions: SUGGESTIONS_BY_STATE[state] || [],
      requiresMoreInfo,
    };
  }

  /**
   * Generates a collecting-state message based on what information is still needed.
   * @private
   */
  _collectingMessage(context, intentResult) {
    const params = context.productParams || {};
    const paramCount = Object.keys(params).length;

    if (intentResult?.intent) {
      if (paramCount === 0) {
        return `I understand you are looking for something related to "${intentResult.intent}". Could you give me more details, such as the product category and your budget?`;
      }
      return `Great, I have captured some details. Could you tell me more about your requirements, such as your budget or preferred brand?`;
    }

    return 'I\'m here to help! Could you describe what you are looking for in more detail?';
  }
}

module.exports = new DialogManager();
module.exports.DialogManager = DialogManager;
