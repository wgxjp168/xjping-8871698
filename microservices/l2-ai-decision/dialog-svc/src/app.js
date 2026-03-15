'use strict';

require('dotenv').config();

const express = require('express');
const morgan = require('morgan');

const config = require('./config/default');
const logger = require('./services/logger');
const healthRouter = require('./routes/health');
const dialogRouter = require('./routes/dialog');
const errorHandler = require('./middleware/errorHandler');

// ─── App setup ────────────────────────────────────────────────────────────────

const app = express();

// Trust proxy headers (e.g. X-Forwarded-For) when running behind a load balancer.
app.set('trust proxy', 1);

// ─── Middleware ───────────────────────────────────────────────────────────────

// HTTP request logging (skip in test environment to keep output clean).
if (process.env.NODE_ENV !== 'test') {
  app.use(morgan('combined', {
    stream: {
      write: (message) => logger.info({ msg: message.trim(), type: 'http' }),
    },
  }));
}

// Parse incoming JSON bodies (limit to 1 MB to guard against payload attacks).
app.use(express.json({ limit: '1mb' }));

// Parse URL-encoded bodies (e.g. form submissions).
app.use(express.urlencoded({ extended: false }));

// ─── Routes ───────────────────────────────────────────────────────────────────

app.use('/', healthRouter);
app.use('/', dialogRouter);

// ─── 404 handler ─────────────────────────────────────────────────────────────

app.use((_req, res) => {
  res.status(404).json({
    code: 'NOT_FOUND',
    message: 'The requested resource was not found.',
    timestamp: new Date().toISOString(),
  });
});

// ─── Global error handler ─────────────────────────────────────────────────────

app.use(errorHandler);

// ─── Server startup ───────────────────────────────────────────────────────────

let server;

if (require.main === module) {
  server = app.listen(config.port, () => {
    logger.info({
      msg: `dialog-svc listening`,
      port: config.port,
      env: process.env.NODE_ENV || 'development',
    });
  });

  // ─── Graceful shutdown ────────────────────────────────────────────────────

  /**
   * Gracefully closes the HTTP server and the Redis connection,
   * allowing in-flight requests to complete before exiting.
   *
   * @param {string} signal - OS signal name (e.g. 'SIGTERM').
   */
  function gracefulShutdown(signal) {
    logger.info({ msg: `Received ${signal} – shutting down gracefully` });

    server.close(async () => {
      logger.info({ msg: 'HTTP server closed' });

      try {
        const sessionStore = require('./services/sessionStore');
        const client = sessionStore.getClient();
        if (client && typeof client.quit === 'function') {
          await client.quit();
          logger.info({ msg: 'Redis connection closed' });
        }
      } catch (err) {
        logger.error({ msg: 'Error closing Redis connection', error: err.message });
      }

      process.exit(0);
    });

    // Force exit after 10 s if graceful shutdown stalls.
    setTimeout(() => {
      logger.error({ msg: 'Graceful shutdown timed out – forcing exit' });
      process.exit(1);
    }, 10_000);
  }

  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  process.on('unhandledRejection', (reason) => {
    logger.error({ msg: 'Unhandled promise rejection', reason: String(reason) });
  });

  process.on('uncaughtException', (err) => {
    logger.error({ msg: 'Uncaught exception', error: err.message, stack: err.stack });
    process.exit(1);
  });
}

module.exports = app;
