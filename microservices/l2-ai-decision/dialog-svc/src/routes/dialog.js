'use strict';

const { Router } = require('express');
const { v4: uuidv4 } = require('uuid');
const authMiddleware = require('../middleware/auth');
const dialogManager = require('../services/dialogManager');
const sessionStore = require('../services/sessionStore');
const logger = require('../services/logger');

const router = Router();

// ─── Helper ───────────────────────────────────────────────────────────────────

/**
 * Wraps an async route handler so that unhandled promise rejections are
 * forwarded to the Express error handler.
 *
 * @param {Function} fn
 * @returns {import('express').RequestHandler}
 */
function asyncHandler(fn) {
  return (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
}

// ─── Routes ───────────────────────────────────────────────────────────────────

/**
 * POST /dialog/session
 *
 * Starts a new dialog session.
 *
 * Body: { userId?: string, message: string }
 * Response: { sessionId, message, state, suggestions, requiresMoreInfo }
 */
router.post(
  '/dialog/session',
  asyncHandler(async (req, res) => {
    const { userId, message } = req.body;

    if (!message || typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({
        code: 'INVALID_BODY',
        message: 'Field "message" is required and must be a non-empty string.',
        timestamp: new Date().toISOString(),
      });
    }

    const resolvedUserId = userId || `anon-${uuidv4()}`;

    const result = await dialogManager.startSession(resolvedUserId, message.trim());

    logger.info({
      msg: 'New dialog session created via API',
      sessionId: result.sessionId,
      userId: resolvedUserId,
    });

    return res.status(201).json(result);
  })
);

/**
 * POST /dialog/message
 *
 * Sends a user message to an existing session.
 * Requires a valid JWT (Authorization: Bearer <token>).
 *
 * Body: { sessionId: string, message: string }
 * Response: { sessionId, message, state, suggestions, requiresMoreInfo }
 */
router.post(
  '/dialog/message',
  authMiddleware,
  asyncHandler(async (req, res) => {
    const { sessionId, message } = req.body;

    if (!sessionId || typeof sessionId !== 'string') {
      return res.status(400).json({
        code: 'INVALID_BODY',
        message: 'Field "sessionId" is required.',
        timestamp: new Date().toISOString(),
      });
    }

    if (!message || typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({
        code: 'INVALID_BODY',
        message: 'Field "message" is required and must be a non-empty string.',
        timestamp: new Date().toISOString(),
      });
    }

    const result = await dialogManager.processMessage(sessionId, message.trim());

    logger.info({
      msg: 'Dialog message processed',
      sessionId,
      userId: req.user?.sub || req.user?.userId,
      state: result.state,
    });

    return res.status(200).json(result);
  })
);

/**
 * GET /dialog/session/:sessionId
 *
 * Returns the current state of a dialog session.
 * Response: full session object (without internal Redis metadata).
 */
router.get(
  '/dialog/session/:sessionId',
  asyncHandler(async (req, res) => {
    const { sessionId } = req.params;

    const session = await sessionStore.get(sessionId);
    if (!session) {
      return res.status(404).json({
        code: 'SESSION_NOT_FOUND',
        message: `Session "${sessionId}" does not exist or has expired.`,
        timestamp: new Date().toISOString(),
      });
    }

    return res.status(200).json(session);
  })
);

/**
 * DELETE /dialog/session/:sessionId
 *
 * Ends (deletes) a dialog session.
 * Response: 204 No Content on success.
 */
router.delete(
  '/dialog/session/:sessionId',
  asyncHandler(async (req, res) => {
    const { sessionId } = req.params;

    const session = await sessionStore.get(sessionId);
    if (!session) {
      return res.status(404).json({
        code: 'SESSION_NOT_FOUND',
        message: `Session "${sessionId}" does not exist or has expired.`,
        timestamp: new Date().toISOString(),
      });
    }

    await sessionStore.delete(sessionId);

    logger.info({ msg: 'Dialog session deleted via API', sessionId });

    return res.status(204).send();
  })
);

/**
 * GET /dialog/history/:sessionId
 *
 * Returns the message history for a dialog session.
 * Response: { sessionId, messages: Array<{ role, content, timestamp }>, turnCount }
 */
router.get(
  '/dialog/history/:sessionId',
  asyncHandler(async (req, res) => {
    const { sessionId } = req.params;

    const session = await sessionStore.get(sessionId);
    if (!session) {
      return res.status(404).json({
        code: 'SESSION_NOT_FOUND',
        message: `Session "${sessionId}" does not exist or has expired.`,
        timestamp: new Date().toISOString(),
      });
    }

    return res.status(200).json({
      sessionId: session.sessionId,
      messages: session.messages,
      turnCount: session.turnCount,
    });
  })
);

module.exports = router;
