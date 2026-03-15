'use strict';

const axios = require('axios');
const config = require('../config/default');
const logger = require('./logger');

/**
 * Axios instance pre-configured for decision-svc.
 */
const httpClient = axios.create({
  baseURL: config.decision.svcUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Response / Error interceptors ───────────────────────────────────────────

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    logger.error({
      msg: 'decisionClient HTTP error',
      url: error.config?.url,
      status: error.response?.status,
      error: error.message,
    });
    return Promise.reject(error);
  }
);

/**
 * Submits the accumulated dialog context to decision-svc for the
 * 8-step AI decision flow.
 *
 * @param {Object} payload
 * @param {string} payload.sessionId
 * @param {string} payload.userId
 * @param {string} payload.intent
 * @param {Array}  payload.entities
 * @param {Object} payload.brandStatus
 * @param {Object} payload.productParams
 * @param {Array}  payload.messages - Full message history.
 * @returns {Promise<{ decisionId: string, status: string, summary: string, steps: Array }>}
 */
async function analyze(payload) {
  const response = await httpClient.post('/decision/analyze', payload);
  return response.data;
}

/**
 * Fetches a previously generated decision report.
 *
 * @param {string} decisionId
 * @returns {Promise<Object>} Decision report object.
 */
async function getReport(decisionId) {
  const response = await httpClient.get(`/decision/report/${decisionId}`);
  return response.data;
}

module.exports = { analyze, getReport };
