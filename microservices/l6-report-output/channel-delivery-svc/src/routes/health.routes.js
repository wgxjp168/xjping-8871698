'use strict';

const express = require('express');
const router = express.Router();
const db = require('../config/database');
const redis = require('../config/redis');

router.get('/health', async (req, res) => {
  const checks = {};

  // DB check
  try {
    await db.raw('SELECT 1');
    checks.db = 'UP';
  } catch { checks.db = 'DOWN'; }

  // Redis check
  try {
    await redis.ping();
    checks.redis = 'UP';
  } catch { checks.redis = 'DOWN'; }

  const overall = Object.values(checks).every(s => s === 'UP') ? 'UP' : 'DEGRADED';
  res.status(overall === 'UP' ? 200 : 503).json({
    status: overall,
    service: 'channel-delivery-svc',
    checks,
    timestamp: new Date().toISOString(),
  });
});

router.get('/health/liveness',  (_req, res) => res.json({ status: 'UP' }));
router.get('/health/readiness', async (req, res) => {
  try {
    await db.raw('SELECT 1');
    res.json({ status: 'UP' });
  } catch {
    res.status(503).json({ status: 'DOWN' });
  }
});

module.exports = router;
