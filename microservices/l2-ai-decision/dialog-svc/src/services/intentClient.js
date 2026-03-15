'use strict';

const axios = require('axios');
const config = require('../config/default');
const logger = require('./logger');

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 200;

/**
 * Creates an axios instance pre-configured for intent-svc.
 */
const httpClient = axios.create({
  baseURL: config.intent.svcUrl,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Executes a request with exponential-backoff retry logic.
 *
 * @param {Function} requestFn - Zero-arg function that returns a Promise<AxiosResponse>.
 * @param {number} [retries=MAX_RETRIES]
 * @param {number} [delay=BASE_DELAY_MS]
 * @returns {Promise<any>} Response data.
 */
async function withRetry(requestFn, retries = MAX_RETRIES, delay = BASE_DELAY_MS) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await requestFn();
      return response.data;
    } catch (err) {
      lastError = err;
      const isRetryable =
        !err.response || err.response.status >= 500 || err.code === 'ECONNREFUSED';

      if (!isRetryable || attempt === retries) {
        logger.error({
          msg: 'intentClient request failed',
          attempt,
          error: err.message,
          status: err.response?.status,
        });
        break;
      }

      const backoff = delay * Math.pow(2, attempt);
      logger.warn({
        msg: `intentClient retry ${attempt + 1}/${retries}`,
        backoffMs: backoff,
        error: err.message,
      });
      await new Promise((resolve) => setTimeout(resolve, backoff));
    }
  }
  throw lastError;
}

/**
 * Recognises the intent of a user utterance.
 *
 * @param {string} text  - Raw user message.
 * @param {Object} [context={}] - Session context passed for multi-turn awareness.
 * @returns {Promise<{ intent: string, confidence: number, raw: Object }>}
 */
async function recognize(text, context = {}) {
  return withRetry(() =>
    httpClient.post('/intent/recognize', { text, context })
  );
}

/**
 * Extracts named entities from a user utterance.
 *
 * @param {string} text
 * @returns {Promise<{ entities: Array<{ type: string, value: string, confidence: number }> }>}
 */
async function extractEntities(text) {
  return withRetry(() =>
    httpClient.post('/entity/extract', { text })
  );
}

/**
 * Detects brand references given text and previously extracted entities.
 *
 * @param {string} text
 * @param {Array}  entities - Output of extractEntities.
 * @returns {Promise<{ brands: string[], status: string }>}
 */
async function detectBrand(text, entities) {
  return withRetry(() =>
    httpClient.post('/brand/detect', { text, entities })
  );
}

module.exports = { recognize, extractEntities, detectBrand };
