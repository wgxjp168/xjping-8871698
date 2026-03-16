'use strict';

const express = require('express');
const { body, param, validationResult } = require('express-validator');
const router = express.Router();

const deliveryOrchestrator = require('../services/deliveryOrchestrator');
const webPortalService = require('../services/webPortalService');
const DeliveryTask = require('../models/DeliveryTask');
const logger = require('../config/logger');

// ── Validation helper ──
const validate = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  next();
};

/**
 * POST /internal/v1/deliveries
 * Called by format-output-svc to trigger multi-channel delivery.
 */
router.post('/',
  [
    body('formatJobNo').notEmpty().isString(),
    body('l5ReportNo').notEmpty().isString(),
    body('userId').notEmpty().isInt({ min: 1 }),
    body('reportTitle').notEmpty().isString(),
    body('clientType').notEmpty().isIn(['B2B', 'B2C_DEFINED', 'B2C_UNDEFINED']),
  ],
  validate,
  async (req, res) => {
    const payload = req.body;
    logger.info(`[DeliveryAPI] Received delivery request for formatJobNo=${payload.formatJobNo}`);

    try {
      // Fire-and-forget (async delivery, return 202 immediately)
      deliveryOrchestrator.orchestrate(payload).catch(err => {
        logger.error(`[DeliveryAPI] Orchestration error: ${err.message}`);
      });

      res.status(202).json({
        status: 'ACCEPTED',
        message: 'Delivery dispatched to all channels',
        formatJobNo: payload.formatJobNo,
      });
    } catch (err) {
      logger.error(`[DeliveryAPI] Error: ${err.message}`);
      res.status(500).json({ error: err.message });
    }
  }
);

/**
 * GET /internal/v1/deliveries/:deliveryNo
 * Query delivery task status and per-channel results.
 */
router.get('/:deliveryNo',
  [param('deliveryNo').notEmpty().isString()],
  validate,
  async (req, res) => {
    try {
      const task = await DeliveryTask.findByDeliveryNo(req.params.deliveryNo);
      if (!task) return res.status(404).json({ error: 'Delivery task not found' });

      const logs = await DeliveryTask.getChannelLogs(task.id);
      res.json({ task, channelLogs: logs });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  }
);

/**
 * GET /internal/v1/deliveries/user/:userId/notifications
 * Retrieve web portal notifications for a user.
 */
router.get('/user/:userId/notifications',
  [param('userId').isInt({ min: 1 })],
  validate,
  async (req, res) => {
    try {
      const notifications = await webPortalService.getUserNotifications(
        parseInt(req.params.userId),
        parseInt(req.query.limit || '20')
      );
      res.json({ userId: req.params.userId, notifications });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  }
);

/**
 * GET /internal/v1/deliveries/access-check/:l5ReportNo/:userId
 * Validate if a user has access to a specific report (for access control).
 */
router.get('/access-check/:l5ReportNo/:userId',
  async (req, res) => {
    try {
      const hasAccess = await webPortalService.checkAccess(
        req.params.l5ReportNo,
        req.params.userId
      );
      res.json({ hasAccess, l5ReportNo: req.params.l5ReportNo, userId: req.params.userId });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  }
);

// ── L7 / L8 Pre-reserved hooks ──

/**
 * POST /internal/v1/deliveries/:deliveryNo/monetize-hook
 * L7 商业变现层预留接口
 */
router.post('/:deliveryNo/monetize-hook', async (req, res) => {
  logger.info(`[L7 Hook] Monetize hook: deliveryNo=${req.params.deliveryNo}`);
  // TODO: implement premium content gating, usage billing, etc.
  res.status(202).json({ status: 'RECEIVED', deliveryNo: req.params.deliveryNo });
});

/**
 * POST /internal/v1/deliveries/:deliveryNo/feedback-hook
 * L8 反馈优化层预留接口
 */
router.post('/:deliveryNo/feedback-hook', async (req, res) => {
  const { rating, comment } = req.body;
  logger.info(`[L8 Hook] Feedback hook: deliveryNo=${req.params.deliveryNo}, rating=${rating}`);
  // TODO: push to L8 feedback & optimization pipeline
  res.status(202).json({ status: 'RECEIVED', deliveryNo: req.params.deliveryNo });
});

module.exports = router;
