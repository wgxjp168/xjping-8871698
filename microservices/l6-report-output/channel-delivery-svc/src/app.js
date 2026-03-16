'use strict';

require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const { register: promRegister } = require('prom-client');

const logger = require('./config/logger');
const db = require('./config/database');
const deliveryRoutes = require('./routes/delivery.routes');
const healthRoutes = require('./routes/health.routes');
const { errorHandler } = require('./middleware/errorHandler');
const { requestLogger } = require('./middleware/requestLogger');

const app = express();
const PORT = process.env.PORT || 8063;

// ── Security ──
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGINS?.split(',') || '*' }));

// ── Rate Limiting ──
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// ── Body Parsing ──
app.use(express.json({ limit: '2mb' }));
app.use(express.urlencoded({ extended: true }));

// ── Logging ──
app.use(requestLogger);

// ── Routes ──
app.use('/internal/v1/deliveries', deliveryRoutes);
app.use('/actuator', healthRoutes);

// ── Prometheus Metrics ──
app.get('/actuator/prometheus', async (req, res) => {
  res.set('Content-Type', promRegister.contentType);
  res.end(await promRegister.metrics());
});

// ── Error Handler ──
app.use(errorHandler);

// ── Startup ──
async function bootstrap() {
  try {
    await db.migrate.latest();
    logger.info('Database migrations applied');

    app.listen(PORT, () => {
      logger.info(`channel-delivery-svc listening on port ${PORT}`);
    });
  } catch (err) {
    logger.error('Startup failed:', err);
    process.exit(1);
  }
}

bootstrap();

module.exports = app;
