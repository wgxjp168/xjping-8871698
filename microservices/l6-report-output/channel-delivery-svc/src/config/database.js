'use strict';

const knex = require('knex');

const db = knex({
  client: 'pg',
  connection: {
    host:     process.env.DB_HOST     || 'localhost',
    port:     parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME     || 'ilbuy_l6',
    user:     process.env.DB_USERNAME || 'ilbuy',
    password: process.env.DB_PASSWORD || 'ilbuy123',
    ssl:      process.env.DB_SSL === 'true' ? { rejectUnauthorized: false } : false,
  },
  pool: {
    min: 2,
    max: 20,
    acquireTimeoutMillis: 30000,
    idleTimeoutMillis: 30000,
  },
  migrations: {
    directory: './src/migrations',
    tableName:  'knex_migrations_delivery',
  },
});

module.exports = db;
