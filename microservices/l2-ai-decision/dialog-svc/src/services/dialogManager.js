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

// ─── 对话建议语（中文） ───────────────────────────────────────────────────────

const SUGGESTIONS_BY_STATE = {
  [DialogState.COLLECTING]: [
    '请告诉我您想要的商品类别',
    '您的预算大概是多少？',
    '您有偏好的品牌吗？',
    '需要什么规格或参数要求？',
  ],
  [DialogState.BRAND_DETECTION]: [
    '请确认您心仪的品牌',
    '是否需要为您推荐同类其他品牌？',
  ],
  [DialogState.DECISION]: [
    '正在分析中，请稍候…',
  ],
  [DialogState.COMPLETED]: [
    '开始新的采购咨询',
    '进一步优化当前推荐',
    '查看完整决策报告',
  ],
  [DialogState.ERROR]: [
    '请换一种方式描述您的需求',
    '重新开始对话',
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

    // 第一轮意图识别，使响应更有针对性
    let intentResult = null;
    try {
      intentResult = await intentClient.recognize(initialMessage, session.context);
    } catch (err) {
      logger.warn({ msg: '首轮意图识别失败', error: err.message });
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
      const err = new Error('会话不存在，请重新开始');
      err.status = 404;
      throw err;
    }

    if (session.state === DialogState.COMPLETED || session.state === DialogState.ERROR) {
      return this._buildResponse(session, null, '本次会话已结束，请开启新的采购咨询。');
    }

    // 1. Append user message
    session = appendMessage(session, 'user', userMessage);

    // 2. 意图识别
    let intentResult = null;
    try {
      intentResult = await intentClient.recognize(userMessage, session.context);
      session = mergeContext(session, { intent: intentResult.intent });
    } catch (err) {
      logger.error({ msg: '意图识别失败', sessionId, error: err.message });
    }

    // 3. 实体提取
    let entityResult = null;
    try {
      entityResult = await intentClient.extractEntities(userMessage);
      if (entityResult?.entities?.length) {
        const merged = [...(session.context.entities || []), ...entityResult.entities];
        // 按 type:value 去重
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
      logger.warn({ msg: '实体提取失败', sessionId, error: err.message });
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
        // 品牌检测
        try {
          const brandResult = await intentClient.detectBrand(
            context.intent || '',
            context.entities
          );
          session = mergeContext(session, { brandStatus: brandResult });
        } catch (err) {
          logger.warn({ msg: '品牌检测失败', error: err.message });
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
      logger.info({ msg: '触发 AI 决策八步流程', sessionId: session.sessionId });

      // ── 单品分析（8步决策流）────────────────────────────────────────────
      const decisionPayload = {
        session_id: session.sessionId,
        intent: session.context.intent || 'PURCHASE_INQUIRY',
        entities: this._entitiesToDict(session.context.entities),
        brand_status: session.context.brandStatus?.brand_status || 'UNKNOWN',
        user_context: {
          userId: session.userId,
          productParams: session.context.productParams,
        },
      };

      const decisionResult = await decisionClient.analyze(decisionPayload);

      // ── 双档推荐（当候选商品数 ≥ 2 时启用）───────────────────────────
      let dualResult = null;
      const candidates = session.context.candidates || [];
      if (candidates.length >= 2) {
        try {
          const dualPayload = {
            session_id: session.sessionId,
            intent: decisionPayload.intent,
            entities: decisionPayload.entities,
            brand_status: decisionPayload.brand_status,
            user_context: decisionPayload.user_context,
            candidates,
          };
          dualResult = await decisionClient.dualRecommend(dualPayload);
          logger.info({
            msg: '双档推荐完成',
            sessionId: session.sessionId,
            qualityPick: dualResult?.quality_pick?.product_name,
            valuePick: dualResult?.value_pick?.product_name,
          });
        } catch (dualErr) {
          logger.warn({ msg: '双档推荐失败，降级为单品分析', error: dualErr.message });
        }
      }

      session = mergeContext(session, { decisionResult, dualResult });
      session = transitionState(session, DialogState.COMPLETED);

      logger.info({
        msg: 'AI 决策流程完成',
        sessionId: session.sessionId,
        decisionId: decisionResult?.decision_id,
      });
    } catch (err) {
      logger.error({
        msg: 'AI 决策流程失败',
        sessionId: session.sessionId,
        error: err.message,
      });
      session = transitionState(session, DialogState.ERROR);
      session = mergeContext(session, { errorMessage: err.message });
    }

    return session;
  }

  /**
   * 将实体数组 [{type, value}] 转为 decision-svc 期望的 dict 格式。
   * @private
   */
  _entitiesToDict(entities) {
    if (!Array.isArray(entities)) return entities || {};
    const dict = {};
    for (const e of entities) {
      if (e && e.type) dict[e.type] = e.value;
    }
    return dict;
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

        case DialogState.BRAND_DETECTION: {
          requiresMoreInfo = true;
          const detectedBrands = context.brandStatus?.brands || [];
          if (detectedBrands.length > 0) {
            message = `我检测到您提到了以下品牌：**${detectedBrands.join('、')}**。\n请问您是否已确定品牌？还是希望我为您推荐更多同类品牌进行对比？`;
          } else {
            message = '我正在分析您的品牌偏好。请问您是否有心仪的品牌，或希望我根据需求为您推荐？';
          }
          break;
        }

        case DialogState.DECISION:
          requiresMoreInfo = false;
          message = '已收集到足够的需求信息，正在运行 AI 决策八步分析，请稍候…';
          break;

        case DialogState.COMPLETED: {
          const decisionId = context.decisionResult?.decision_id;
          const dualResult = context.dualResult;

          if (dualResult) {
            // 双档推荐摘要
            const q = dualResult.quality_pick;
            const v = dualResult.value_pick;
            message = `🎯 **AI 采购分析完成！**\n\n` +
              `**品质款推荐**：${q.product_name}（评分 ${q.score_result?.total_score?.toFixed(1)}，` +
              `价格 ¥${q.product_price?.toFixed(2)}）\n` +
              `**性价比款推荐**：${v.product_name}（评分 ${v.score_result?.total_score?.toFixed(1)}，` +
              `价格 ¥${v.product_price?.toFixed(2)}）\n\n` +
              `${dualResult.comparison_summary || ''}\n\n` +
              `决策报告编号：\`${decisionId || dualResult.decision_id}\``;
          } else if (decisionId) {
            const score = context.decisionResult?.score_result?.total_score;
            const grade = context.decisionResult?.score_result?.grade;
            const rec = context.decisionResult?.recommendation || '';
            message = `🎯 **AI 采购分析完成！**\n\n` +
              `综合评分：**${score?.toFixed(1) ?? '--'} 分（${grade ?? '--'} 级）**\n\n` +
              `${rec}\n\n` +
              `决策报告编号：\`${decisionId}\`，可通过报告 ID 查看完整分析。`;
          } else {
            message = '本次采购咨询已完成。如需重新咨询，请开启新会话。';
          }
          break;
        }

        case DialogState.ERROR:
          message = `❌ 处理您的请求时出现错误：${context.errorMessage || '未知错误'}。\n请尝试重新描述需求，或开启新会话。`;
          break;

        default:
          message = '您好！我是 ILbuy 智能采购助手，请告诉我您的采购需求。';
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
    const entityCount = (context.entities || []).length;

    const INTENT_CN_MAP = {
      PURCHASE_INQUIRY: '购买咨询',
      RECOMMENDATION: '商品推荐',
      PRICE_QUERY: '价格查询',
      SPEC_QUERY: '规格查询',
      COMPARISON: '商品对比',
      BUDGET_INQUIRY: '预算规划',
      CUSTOM_ORDER: '企业定制采购',
      BRAND_QUERY: '品牌咨询',
    };

    if (intentResult?.intent) {
      const intentCn = INTENT_CN_MAP[intentResult.intent] || intentResult.intent;
      if (paramCount === 0 && entityCount === 0) {
        return `您好！我了解您正在咨询**${intentCn}**相关内容。\n请告诉我更多细节，例如：商品类别、预算范围，以及是否有偏好的品牌？`;
      }
      if (paramCount < MIN_PARAMS_FOR_DECISION) {
        const missing = [];
        if (!params.budget_max && !params.budget_min) missing.push('预算范围');
        if (!params.category) missing.push('商品类别');
        if (!params.brand) missing.push('品牌偏好（可选）');
        const hint = missing.length > 0 ? `\n\n还需要您提供：${missing.join('、')}` : '';
        return `好的，我已记录了您的部分需求（共 ${paramCount} 项参数）。${hint}`;
      }
      return `好的，我已收集到足够信息（${paramCount} 项参数，${entityCount} 个实体），即将为您进行 AI 决策分析。`;
    }

    return '您好！我是 ILbuy 智能采购助手，请详细描述您的采购需求，例如商品类别、预算和偏好。';
  }
}

module.exports = new DialogManager();
module.exports.DialogManager = DialogManager;
