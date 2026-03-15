'use strict';

const Redis = require('ioredis');
const config = require('../config/default');
const logger = require('./logger');

let _client = null;

/**
 * Returns (and lazily initialises) the shared Redis client.
 * Exported so tests can substitute a mock.
 */
function getClient() {
  if (_client) return _client;

  _client = new Redis(config.redis.url, {
    lazyConnect: true,
    maxRetriesPerRequest: 3,
    enableReadyCheck: true,
    reconnectOnError(err) {
      logger.warn({ msg: 'Redis reconnectOnError', error: err.message });
      return true;
    },
  });

  _client.on('error', (err) => {
    logger.error({ msg: 'Redis client error', error: err.message });
  });

  _client.on('connect', () => {
    logger.info('Redis client connected');
  });

  return _client;
}

/**
 * Replaces the internal Redis client – used in unit tests.
 * @param {object} mockClient
 */
function setClient(mockClient) {
  _client = mockClient;
}

const SESSION_PREFIX = 'dialog:session:';

function key(sessionId) {
  return `${SESSION_PREFIX}${sessionId}`;
}

/**
 * Persists a new session in Redis with the configured TTL.
 *
 * @param {string} sessionId
 * @param {Object} data
 * @returns {Promise<void>}
 */
async function create(sessionId, data) {
  const client = getClient();
  const ttl = config.session.ttl;
  await client.set(key(sessionId), JSON.stringify(data), 'EX', ttl);
  logger.debug({ msg: 'Session created', sessionId, ttl });
}

/**
 * Retrieves a session from Redis.
 *
 * @param {string} sessionId
 * @returns {Promise<Object|null>} Parsed session object, or null if not found.
 */
async function get(sessionId) {
  const client = getClient();
  const raw = await client.get(key(sessionId));
  if (!raw) return null;
  return JSON.parse(raw);
}

/**
 * Overwrites a session in Redis, preserving the remaining TTL.
 *
 * @param {string} sessionId
 * @param {Object} data
 * @returns {Promise<void>}
 */
async function update(sessionId, data) {
  const client = getClient();
  const ttlRemaining = await client.ttl(key(sessionId));
  const effectiveTtl = ttlRemaining > 0 ? ttlRemaining : config.session.ttl;
  await client.set(key(sessionId), JSON.stringify(data), 'EX', effectiveTtl);
  logger.debug({ msg: 'Session updated', sessionId });
}

/**
 * Removes a session from Redis.
 *
 * @param {string} sessionId
 * @returns {Promise<void>}
 */
async function del(sessionId) {
  const client = getClient();
  await client.del(key(sessionId));
  logger.debug({ msg: 'Session deleted', sessionId });
}

/**
 * Resets the TTL of an existing session.
 *
 * @param {string} sessionId
 * @param {number} [ttl] - Seconds; defaults to config value.
 * @returns {Promise<void>}
 */
async function expire(sessionId, ttl) {
  const client = getClient();
  const effectiveTtl = ttl || config.session.ttl;
  await client.expire(key(sessionId), effectiveTtl);
  logger.debug({ msg: 'Session TTL refreshed', sessionId, ttl: effectiveTtl });
}

module.exports = {
  getClient,
  setClient,
  create,
  get,
  update,
  delete: del,
  expire,
};
