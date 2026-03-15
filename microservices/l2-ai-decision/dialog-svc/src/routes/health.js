'use strict';

const { Router } = require('express');

const router = Router();

/**
 * GET /health
 *
 * Liveness / readiness probe endpoint.
 * Returns a simple JSON payload confirming the service is running.
 */
router.get('/health', (_req, res) => {
  res.status(200).json({
    status: 'ok',
    service: 'dialog-svc',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
  });
});

module.exports = router;
