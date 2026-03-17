'use strict';

module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/tests/**/*.test.js'],
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/migrations/**',
    '!src/app.js',          // Integration bootstrap excluded from unit coverage
    '!src/config/**',       // Infrastructure config (always mocked; covered by integration tests)
  ],
  coverageThreshold: {
    global: {
      branches:   60,
      functions:  70,
      lines:      70,
      statements: 70,
    },
  },
  coverageReporters: ['text', 'lcov', 'html'],
  testTimeout: 10000,
  verbose: true,
  // Silence console.log noise in tests
  silent: false,
};
