'use strict';

const logger = require('../services/logger');

/**
 * Maps well-known error status codes to short error codes.
 */
const STATUS_TO_CODE = {
  400: 'BAD_REQUEST',
  401: 'UNAUTHORIZED',
  403: 'FORBIDDEN',
  404: 'NOT_FOUND',
  409: 'CONFLICT',
  422: 'UNPROCESSABLE_ENTITY',
  429: 'TOO_MANY_REQUESTS',
  500: 'INTERNAL_SERVER_ERROR',
  502: 'BAD_GATEWAY',
  503: 'SERVICE_UNAVAILABLE',
};

/**
 * Centralised Express error-handling middleware.
 *
 * Must be registered AFTER all routes and other middleware (4-parameter signature
 * signals to Express that this is an error handler).
 *
 * Returns a uniform JSON error envelope:
 * {
 *   "code":      "SHORT_ERROR_CODE",
 *   "message":   "Human-readable description",
 *   "timestamp": "2024-01-01T00:00:00.000Z"
 * }
 *
 * @type {import('express').ErrorRequestHandler}
 */
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  const status = err.status || err.statusCode || 500;
  const code = err.code || STATUS_TO_CODE[status] || 'INTERNAL_SERVER_ERROR';
  const message =
    status < 500
      ? err.message || 'An error occurred'
      : 'An unexpected error occurred. Please try again later.';

  // Log all errors; include stack trace only for server errors.
  if (status >= 500) {
    logger.error({
      msg: 'Unhandled server error',
      code,
      status,
      error: err.message,
      stack: err.stack,
      method: req.method,
      url: req.originalUrl,
      requestId: req.id,
    });
  } else {
    logger.warn({
      msg: 'Client error',
      code,
      status,
      error: err.message,
      method: req.method,
      url: req.originalUrl,
      requestId: req.id,
    });
  }

  res.status(status).json({
    code,
    message,
    timestamp: new Date().toISOString(),
  });
}

module.exports = errorHandler;
