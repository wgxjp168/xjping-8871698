'use strict';

require('dotenv').config();

const config = {
  port: parseInt(process.env.PORT, 10) || 8013,

  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
  },

  auth: {
    svcUrl: process.env.AUTH_SVC_URL || '',
  },

  intent: {
    svcUrl: process.env.INTENT_SVC_URL || 'http://localhost:8010',
  },

  decision: {
    svcUrl: process.env.DECISION_SVC_URL || 'http://localhost:8012',
  },

  jwt: {
    secret: process.env.JWT_SECRET || 'ilbuy-dialog-svc-dev-secret',
  },

  session: {
    ttl: parseInt(process.env.SESSION_TTL, 10) || 3600,
  },

  log: {
    level: process.env.LOG_LEVEL || 'info',
  },
};

module.exports = config;
