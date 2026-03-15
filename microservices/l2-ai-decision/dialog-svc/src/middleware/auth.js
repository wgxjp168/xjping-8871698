'use strict';

const jwt = require('jsonwebtoken');
const axios = require('axios');
const config = require('../config/default');
const logger = require('../services/logger');

/**
 * Extracts the Bearer token from the Authorization header.
 *
 * @param {import('express').Request} req
 * @returns {string|null} Raw JWT string, or null if absent/malformed.
 */
function extractToken(req) {
  const header = req.headers['authorization'] || '';
  if (!header.startsWith('Bearer ')) return null;
  return header.slice(7).trim() || null;
}

/**
 * Verifies the token locally using the configured JWT secret.
 *
 * @param {string} token
 * @returns {{ valid: boolean, payload: Object|null, error: string|null }}
 */
function verifyLocal(token) {
  try {
    const payload = jwt.verify(token, config.jwt.secret);
    return { valid: true, payload, error: null };
  } catch (err) {
    return { valid: false, payload: null, error: err.message };
  }
}

/**
 * Forwards the token to the remote auth service for validation.
 * Falls back to local verification on network/timeout errors.
 *
 * @param {string} token
 * @returns {Promise<{ valid: boolean, payload: Object|null, error: string|null }>}
 */
async function verifyRemote(token) {
  try {
    const response = await axios.post(
      `${config.auth.svcUrl}/auth/verify`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000,
      }
    );
    const payload = response.data?.user || response.data?.payload || response.data;
    return { valid: true, payload, error: null };
  } catch (err) {
    if (err.response) {
      // Auth service explicitly rejected the token.
      return {
        valid: false,
        payload: null,
        error: err.response.data?.message || 'Token rejected by auth service',
      };
    }
    // Network / timeout: fall back to local verification.
    logger.warn({
      msg: 'Auth service unreachable – falling back to local JWT verification',
      error: err.message,
    });
    return verifyLocal(token);
  }
}

/**
 * Express middleware that authenticates requests via JWT.
 *
 * Strategy:
 *  1. Extract Bearer token.
 *  2. If AUTH_SVC_URL is configured, forward to the auth service (with local fallback).
 *  3. Otherwise, verify locally.
 *  4. Attach decoded payload to req.user and call next().
 *
 * @type {import('express').RequestHandler}
 */
async function authMiddleware(req, res, next) {
  const token = extractToken(req);

  if (!token) {
    return res.status(401).json({
      code: 'MISSING_TOKEN',
      message: 'Authorization header with Bearer token is required',
      timestamp: new Date().toISOString(),
    });
  }

  let result;
  if (config.auth.svcUrl) {
    result = await verifyRemote(token);
  } else {
    result = verifyLocal(token);
  }

  if (!result.valid) {
    logger.warn({ msg: 'JWT verification failed', error: result.error });
    return res.status(401).json({
      code: 'INVALID_TOKEN',
      message: result.error || 'Invalid or expired token',
      timestamp: new Date().toISOString(),
    });
  }

  req.user = result.payload;
  next();
}

module.exports = authMiddleware;
