'use strict';

module.exports = {
  // Server
  PORT: process.env.PORT || 8063,
  NODE_ENV: process.env.NODE_ENV || 'development',

  // Email
  EMAIL_HOST:     process.env.EMAIL_HOST     || 'smtp.example.com',
  EMAIL_PORT:     parseInt(process.env.EMAIL_PORT || '587'),
  EMAIL_USER:     process.env.EMAIL_USER     || '',
  EMAIL_PASS:     process.env.EMAIL_PASS     || '',
  EMAIL_FROM:     process.env.EMAIL_FROM     || '我来购ILbuy <noreply@ilbuy.com>',
  EMAIL_SECURE:   process.env.EMAIL_SECURE   === 'true',

  // WeChat Official Account
  WECHAT_APP_ID:      process.env.WECHAT_APP_ID      || '',
  WECHAT_APP_SECRET:  process.env.WECHAT_APP_SECRET  || '',
  WECHAT_API_BASE:    process.env.WECHAT_API_BASE     || 'https://api.weixin.qq.com',
  WECHAT_TEMPLATE_ID: process.env.WECHAT_TEMPLATE_ID || '',

  // Web Portal
  WEB_PORTAL_URL:     process.env.WEB_PORTAL_URL     || 'https://app.ilbuy.com',

  // Mobile Push (FCM / APNs unified gateway)
  PUSH_GATEWAY_URL:   process.env.PUSH_GATEWAY_URL   || '',
  PUSH_API_KEY:       process.env.PUSH_API_KEY        || '',

  // JWT
  JWT_SECRET: process.env.JWT_SECRET || 'ilbuy-jwt-secret-key-2024-production-use-256bit',

  // Internal service URLs
  L6_FORMAT_OUTPUT_SVC_URL: process.env.L6_FORMAT_OUTPUT_SVC_URL || 'http://localhost:8062',
};
