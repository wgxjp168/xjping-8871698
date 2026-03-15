'use strict';

const { v4: uuidv4 } = require('uuid');

/**
 * Valid dialog session states.
 */
const DialogState = Object.freeze({
  INIT: 'INIT',
  COLLECTING: 'COLLECTING',
  BRAND_DETECTION: 'BRAND_DETECTION',
  DECISION: 'DECISION',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
});

/**
 * Creates a new dialog session object.
 *
 * @param {string} userId  - Authenticated user identifier.
 * @param {string} [sessionId] - Optional explicit session ID; generated if omitted.
 * @returns {Object} Fresh dialog session.
 */
function createSession(userId, sessionId) {
  const now = new Date().toISOString();
  return {
    sessionId: sessionId || uuidv4(),
    userId,
    state: DialogState.INIT,
    messages: [],         // Array of { role: 'user'|'assistant', content, timestamp }
    context: {
      intent: null,       // Last recognised intent name
      entities: [],       // Extracted named entities
      brandStatus: null,  // Result from brand detection
      productParams: {},  // Accumulated product / requirement parameters
    },
    turnCount: 0,
    createdAt: now,
    updatedAt: now,
  };
}

/**
 * Appends a message to the session's message log and bumps turnCount for
 * user messages.
 *
 * @param {Object} session - Existing session object (mutated in-place copy).
 * @param {'user'|'assistant'} role
 * @param {string} content
 * @returns {Object} Updated session.
 */
function appendMessage(session, role, content) {
  const updated = { ...session };
  updated.messages = [
    ...session.messages,
    { role, content, timestamp: new Date().toISOString() },
  ];
  if (role === 'user') {
    updated.turnCount = (session.turnCount || 0) + 1;
  }
  updated.updatedAt = new Date().toISOString();
  return updated;
}

/**
 * Merges new context fields into the session context.
 *
 * @param {Object} session
 * @param {Object} contextPatch
 * @returns {Object} Updated session.
 */
function mergeContext(session, contextPatch) {
  return {
    ...session,
    context: {
      ...session.context,
      ...contextPatch,
    },
    updatedAt: new Date().toISOString(),
  };
}

/**
 * Transitions the session to a new state.
 *
 * @param {Object} session
 * @param {string} newState - One of DialogState values.
 * @returns {Object} Updated session.
 */
function transitionState(session, newState) {
  if (!Object.values(DialogState).includes(newState)) {
    throw new Error(`Invalid dialog state: ${newState}`);
  }
  return {
    ...session,
    state: newState,
    updatedAt: new Date().toISOString(),
  };
}

module.exports = {
  DialogState,
  createSession,
  appendMessage,
  mergeContext,
  transitionState,
};
