'use strict';

require('dotenv').config();

/**
 * Knex configuration for CLI migrations.
 * Usage:
 *   npx knex migrate:latest --env development
 *   npx knex migrate:latest --env production
 *   npx knex migrate:rollback --env development
 */
module.exports = {
  development: {
    client: 'pg',
    connection: {
      host:     process.env.DB_HOST     || 'localhost',
      port:     parseInt(process.env.DB_PORT || '5432'),
      database: process.env.DB_NAME     || 'ilbuy_l6',
      user:     process.env.DB_USERNAME || 'ilbuy',
      password: process.env.DB_PASSWORD || 'ilbuy123',
    },
    pool: { min: 2, max: 10 },
    migrations: {
      directory: './src/migrations',
      tableName:  'knex_migrations_delivery',
    },
    debug: true,
  },

  production: {
    client: 'pg',
    connection: {
      host:     process.env.DB_HOST,
      port:     parseInt(process.env.DB_PORT || '5432'),
      database: process.env.DB_NAME,
      user:     process.env.DB_USERNAME,
      password: process.env.DB_PASSWORD,
      ssl:      { rejectUnauthorized: false },
    },
    pool: { min: 2, max: 20 },
    migrations: {
      directory: './src/migrations',
      tableName:  'knex_migrations_delivery',
    },
  },

  test: {
    client: 'pg',
    connection: {
      host:     process.env.DB_HOST     || 'localhost',
      port:     parseInt(process.env.DB_PORT || '5432'),
      database: process.env.DB_TEST_NAME || 'ilbuy_l6_test',
      user:     process.env.DB_USERNAME  || 'ilbuy',
      password: process.env.DB_PASSWORD  || 'ilbuy123',
    },
    pool: { min: 1, max: 5 },
    migrations: {
      directory: './src/migrations',
      tableName:  'knex_migrations_delivery',
    },
  },
};
