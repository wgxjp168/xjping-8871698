'use strict';

const logger = require('../config/logger');

const errorHandler = (err, req, res, _next) => {
  logger.error(`Unhandled error: ${err.message}`, { stack: err.stack, path: req.path });
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
    timestamp: new Date().toISOString(),
  });
};

module.exports = { errorHandler };
