'use strict';

const Redis = require('ioredis');
const logger = require('./logger');

const redis = new Redis({
  host:     process.env.REDIS_HOST     || 'localhost',
  port:     parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD || undefined,
  maxRetriesPerRequest: 3,
  retryStrategy: (times) => Math.min(times * 100, 3000),
  lazyConnect: false,
});

redis.on('connect',   () => logger.info('[Redis] Connected'));
redis.on('error',     (e) => logger.error('[Redis] Error:', e.message));
redis.on('reconnecting', () => logger.warn('[Redis] Reconnecting...'));

module.exports = redis;
