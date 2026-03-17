'use strict';

// Mock all external I/O before requiring service modules
jest.mock('../src/config/env', () => ({
  PORT:               8063,
  NODE_ENV:           'test',
  DB_URL:             'postgresql://test:test@localhost:5432/test',
  REDIS_URL:          'redis://localhost:6379',
  RABBITMQ_URL:       'amqp://localhost:5672',
  JWT_SECRET:         'test-secret-key',
  EMAIL_HOST:         'localhost',
  EMAIL_PORT:         25,
  EMAIL_SECURE:       false,
  EMAIL_USER:         '',
  EMAIL_PASS:         '',
  EMAIL_FROM:         'noreply@test.com',
  WECHAT_APP_ID:      '',            // empty → sendTemplateMessage always skips
  WECHAT_APP_SECRET:  '',
  WECHAT_TEMPLATE_ID: 'tmpl-test',
  WECHAT_API_BASE:    'https://api.weixin.qq.com',
  WEB_PORTAL_URL:     'https://app.test.com',
  CORS_ORIGINS:       'https://app.test.com',
  PUSH_GATEWAY_URL:   'http://push.test.com',  // set so push tests proceed past guard
  PUSH_API_KEY:       'test-push-api-key',
  LOG_LEVEL:          'silent',
}));

jest.mock('../src/config/redis', () => ({
  on:      jest.fn(),
  get:     jest.fn(),
  setex:   jest.fn(),
  lpush:   jest.fn(),
  ltrim:   jest.fn(),
  expire:  jest.fn(),
  publish: jest.fn(),
  hset:    jest.fn(),
  hgetall: jest.fn(),
  lrange:  jest.fn(),
}));

jest.mock('nodemailer', () => ({
  createTransport: jest.fn(() => ({
    verify:   jest.fn().mockResolvedValue(true),
    close:    jest.fn(),
    sendMail: jest.fn().mockResolvedValue({
      messageId: 'msg-001',
      accepted:  ['buyer@corp.com'],
    }),
  })),
}));

jest.mock('axios');

const redis        = require('../src/config/redis');
const axios        = require('axios');
const emailService = require('../src/services/emailService');
const wechatService  = require('../src/services/wechatService');
const appPushService = require('../src/services/appPushService');
const webPortal    = require('../src/services/webPortalService');

// ─── EmailService ─────────────────────────────────────────────────────────────

describe('EmailService — pure helpers', () => {
  const opts = {
    reportTitle: 'Q1采购报告',
    clientType:  'B2B',
    htmlUrl:     'http://minio/report.html',
    pdfUrl:      'http://minio/report.pdf',
    excelUrl:    'http://minio/report.xlsx',
    l5ReportNo:  'RPT-20240101-001',
    to:          'buyer@corp.com',
  };

  describe('clientTypeLabel', () => {
    test.each([
      ['B2B',           'B2B企业采购'],
      ['B2C_DEFINED',   'B2C品牌深度'],
      ['B2C_UNDEFINED', 'B2C品牌发现'],
      ['UNKNOWN',       'UNKNOWN'],
    ])('label for %s is %s', (type, expected) => {
      expect(emailService.clientTypeLabel(type)).toBe(expected);
    });
  });

  describe('buildEmailText', () => {
    test('includes reportTitle, reportNo and all URLs', () => {
      const text = emailService.buildEmailText(opts);
      expect(text).toContain('Q1采购报告');
      expect(text).toContain('RPT-20240101-001');
      expect(text).toContain('http://minio/report.html');
      expect(text).toContain('http://minio/report.pdf');
      expect(text).toContain('http://minio/report.xlsx');
    });

    test('omits lines for missing URLs', () => {
      const text = emailService.buildEmailText({ ...opts, excelUrl: undefined });
      expect(text).not.toContain('http://minio/report.xlsx');
    });

    test('returns a non-empty string', () => {
      expect(emailService.buildEmailText(opts).length).toBeGreaterThan(50);
    });
  });

  describe('buildEmailHtml', () => {
    test('returns valid HTML document', () => {
      const html = emailService.buildEmailHtml(opts);
      expect(html).toContain('<!DOCTYPE html>');
      expect(html).toContain('</html>');
    });

    test('contains report title and report number', () => {
      const html = emailService.buildEmailHtml(opts);
      expect(html).toContain('Q1采购报告');
      expect(html).toContain('RPT-20240101-001');
    });

    test('renders download buttons for all provided URLs', () => {
      const html = emailService.buildEmailHtml(opts);
      expect(html).toContain('在线浏览报告');
      expect(html).toContain('下载PDF');
      expect(html).toContain('下载Excel数据');
    });

    test('omits PDF button when pdfUrl is absent', () => {
      const html = emailService.buildEmailHtml({ ...opts, pdfUrl: undefined });
      expect(html).not.toContain('下载PDF');
    });

    test('omits Excel button when excelUrl is absent', () => {
      const html = emailService.buildEmailHtml({ ...opts, excelUrl: undefined });
      expect(html).not.toContain('下载Excel数据');
    });

    test('embeds client type label in header', () => {
      const html = emailService.buildEmailHtml(opts);
      expect(html).toContain('B2B企业采购');
    });
  });

  describe('sendReportEmail', () => {
    test('sends email and returns messageId and accepted list', async () => {
      const result = await emailService.sendReportEmail(opts);
      expect(result.messageId).toBe('msg-001');
      expect(result.accepted).toEqual(['buyer@corp.com']);
    });

    test('calls transporter.sendMail with correct to and subject', async () => {
      const sendMailSpy = jest
        .spyOn(emailService.transporter, 'sendMail')
        .mockResolvedValueOnce({ messageId: 'spy-id', accepted: ['buyer@corp.com'] });

      await emailService.sendReportEmail(opts);

      expect(sendMailSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          to:      'buyer@corp.com',
          subject: expect.stringContaining('Q1采购报告'),
        }),
      );
    });
  });

  describe('verifyConnection', () => {
    test('returns true when SMTP verify succeeds', async () => {
      const result = await emailService.verifyConnection();
      expect(result).toBe(true);
    });

    test('returns false when SMTP verify throws', async () => {
      const nodemailer = require('nodemailer');
      nodemailer.createTransport().verify.mockRejectedValueOnce(new Error('SMTP error'));
      // re-instantiate is not needed; verify is already mock on the existing transporter
      // so we override on the instance directly
      emailService.transporter.verify = jest.fn().mockRejectedValueOnce(new Error('SMTP error'));
      const result = await emailService.verifyConnection();
      expect(result).toBe(false);
    });
  });

  describe('closeConnections', () => {
    test('calls transporter.close()', () => {
      const closeSpy = jest.spyOn(emailService.transporter, 'close');
      emailService.closeConnections();
      expect(closeSpy).toHaveBeenCalled();
    });
  });
});

// ─── WechatService ────────────────────────────────────────────────────────────

describe('WechatService', () => {
  beforeEach(() => jest.clearAllMocks());

  test('clientTypeLabel maps all client types correctly', () => {
    expect(wechatService.clientTypeLabel('B2B')).toBe('B2B企业采购');
    expect(wechatService.clientTypeLabel('B2C_DEFINED')).toBe('B2C已定品牌');
    expect(wechatService.clientTypeLabel('B2C_UNDEFINED')).toBe('B2C品牌发现');
    expect(wechatService.clientTypeLabel('CUSTOM')).toBe('CUSTOM');
  });

  test('sendTemplateMessage returns {skipped:true} when openId is null', async () => {
    const result = await wechatService.sendTemplateMessage({
      openId: null, reportTitle: 'Test', clientType: 'B2B', l5ReportNo: 'RPT-001',
    });
    expect(result).toEqual({ skipped: true });
  });

  test('sendTemplateMessage returns {skipped:true} when openId is empty string', async () => {
    const result = await wechatService.sendTemplateMessage({
      openId: '', reportTitle: 'Test', clientType: 'B2B', l5ReportNo: 'RPT-001',
    });
    expect(result).toEqual({ skipped: true });
  });

  test('getAccessToken returns cached token from Redis', async () => {
    redis.get.mockResolvedValue('cached-access-token-xyz');
    const token = await wechatService.getAccessToken();
    expect(token).toBe('cached-access-token-xyz');
    expect(redis.get).toHaveBeenCalledWith('wechat:access_token');
    expect(axios.get).not.toHaveBeenCalled();
  });

  test('getAccessToken fetches and caches new token when cache is empty', async () => {
    redis.get.mockResolvedValue(null);
    axios.get.mockResolvedValue({ data: { access_token: 'new-token-abc', expires_in: 7200 } });

    const token = await wechatService.getAccessToken();
    expect(token).toBe('new-token-abc');
    expect(redis.setex).toHaveBeenCalledWith('wechat:access_token', 7000, 'new-token-abc');
  });

  test('getAccessToken throws when WeChat API returns errcode', async () => {
    redis.get.mockResolvedValue(null);
    axios.get.mockResolvedValue({ data: { errcode: 40013, errmsg: 'invalid appid' } });

    await expect(wechatService.getAccessToken()).rejects.toThrow('WeChat token error');
  });
});

// ─── AppPushService ───────────────────────────────────────────────────────────

describe('AppPushService', () => {
  beforeEach(() => jest.clearAllMocks());

  test('returns {skipped:true} when deviceToken is null', async () => {
    const result = await appPushService.sendPush({
      deviceToken: null, reportTitle: 'Test', l5ReportNo: 'RPT-001',
    });
    expect(result).toEqual({ skipped: true });
  });

  test('returns {skipped:true} when deviceToken is empty string', async () => {
    const result = await appPushService.sendPush({
      deviceToken: '', reportTitle: 'Test', l5ReportNo: 'RPT-001',
    });
    expect(result).toEqual({ skipped: true });
  });

  test('sends push successfully via axios when configured', async () => {
    process.env.PUSH_GATEWAY_URL = 'http://push.test.com';
    axios.post.mockResolvedValue({ status: 200, data: { success: true, msgid: 'push-123' } });

    const result = await appPushService.sendPush({
      deviceToken: 'device-token-abc123',
      reportTitle: 'Q1采购报告',
      l5ReportNo:  'RPT-001',
      htmlUrl:     'http://minio/report.html',
      clientType:  'B2B',
    });

    expect(result.success).toBe(true);
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/v1/push'),
      expect.objectContaining({ token: 'device-token-abc123' }),
      expect.any(Object),
    );
  });

  test('propagates error when push gateway fails', async () => {
    process.env.PUSH_GATEWAY_URL = 'http://push.test.com';
    axios.post.mockRejectedValue(new Error('Connection refused'));

    await expect(appPushService.sendPush({
      deviceToken: 'device-token-xyz',
      reportTitle: 'Test',
      l5ReportNo:  'RPT-002',
    })).rejects.toThrow('Connection refused');
  });
});

// ─── errorHandler middleware ──────────────────────────────────────────────────

describe('errorHandler middleware', () => {
  const { errorHandler } = require('../src/middleware/errorHandler');

  test('returns 500 with error message for unhandled error', () => {
    const err = new Error('Something went wrong');
    const req = { path: '/test' };
    const res = { status: jest.fn().mockReturnThis(), json: jest.fn() };
    const next = jest.fn();

    errorHandler(err, req, res, next);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: 'Something went wrong' }),
    );
  });

  test('uses err.status when present', () => {
    const err = Object.assign(new Error('Not found'), { status: 404 });
    const req = { path: '/test' };
    const res = { status: jest.fn().mockReturnThis(), json: jest.fn() };

    errorHandler(err, req, res, jest.fn());

    expect(res.status).toHaveBeenCalledWith(404);
  });
});

// ─── WebPortalService ─────────────────────────────────────────────────────────

describe('WebPortalService', () => {
  beforeEach(() => jest.clearAllMocks());

  const notifyOpts = {
    userId:      42,
    l5ReportNo:  'RPT-TEST-001',
    reportTitle: 'Q2报告',
    clientType:  'B2B',
    htmlUrl:     'http://minio/q2.html',
    pdfUrl:      'http://minio/q2.pdf',
    excelUrl:    'http://minio/q2.xlsx',
  };

  describe('notifyReportReady', () => {
    beforeEach(() => {
      redis.lpush.mockResolvedValue(1);
      redis.ltrim.mockResolvedValue('OK');
      redis.expire.mockResolvedValue(1);
      redis.publish.mockResolvedValue(0);
      redis.hset.mockResolvedValue(1);
    });

    test('returns notificationStored=true', async () => {
      const result = await webPortal.notifyReportReady(notifyOpts);
      expect(result.notificationStored).toBe(true);
    });

    test('pushes notification to user-specific Redis list', async () => {
      await webPortal.notifyReportReady(notifyOpts);
      expect(redis.lpush).toHaveBeenCalledWith('notifications:user:42', expect.any(String));
      expect(redis.ltrim).toHaveBeenCalledWith('notifications:user:42', 0, 49);
    });

    test('publishes to Pub/Sub channel for SSE delivery', async () => {
      await webPortal.notifyReportReady(notifyOpts);
      expect(redis.publish).toHaveBeenCalledWith('report:ready:user:42', expect.any(String));
    });

    test('stores access metadata hash for the report', async () => {
      await webPortal.notifyReportReady(notifyOpts);
      expect(redis.hset).toHaveBeenCalledWith(
        'report:access:RPT-TEST-001',
        expect.objectContaining({ userId: '42' }),
      );
    });

    test('returns the Pub/Sub channel name', async () => {
      const result = await webPortal.notifyReportReady(notifyOpts);
      expect(result.pubChannel).toBe('report:ready:user:42');
    });
  });

  describe('checkAccess', () => {
    test('returns true when userId matches stored metadata', async () => {
      redis.hgetall.mockResolvedValue({ userId: '42', htmlUrl: 'http://...', expiresAt: '...' });
      await expect(webPortal.checkAccess('RPT-TEST-001', 42)).resolves.toBe(true);
    });

    test('returns false when userId does not match', async () => {
      redis.hgetall.mockResolvedValue({ userId: '99' });
      await expect(webPortal.checkAccess('RPT-TEST-001', 42)).resolves.toBe(false);
    });

    test('returns false when no metadata exists in Redis', async () => {
      redis.hgetall.mockResolvedValue(null);
      await expect(webPortal.checkAccess('RPT-TEST-001', 42)).resolves.toBe(false);
    });

    test('returns false when metadata exists but userId field is missing', async () => {
      redis.hgetall.mockResolvedValue({ htmlUrl: 'http://...' });
      await expect(webPortal.checkAccess('RPT-TEST-001', 42)).resolves.toBe(false);
    });
  });

  describe('getUserNotifications', () => {
    test('parses and returns JSON items from Redis list', async () => {
      const items = [
        JSON.stringify({ type: 'REPORT_READY', l5ReportNo: 'RPT-001' }),
        JSON.stringify({ type: 'REPORT_READY', l5ReportNo: 'RPT-002' }),
      ];
      redis.lrange.mockResolvedValue(items);

      const result = await webPortal.getUserNotifications(42);
      expect(result).toHaveLength(2);
      expect(result[0].l5ReportNo).toBe('RPT-001');
      expect(result[1].l5ReportNo).toBe('RPT-002');
    });

    test('returns empty array when no notifications', async () => {
      redis.lrange.mockResolvedValue([]);
      const result = await webPortal.getUserNotifications(42);
      expect(result).toEqual([]);
    });

    test('passes limit to Redis lrange', async () => {
      redis.lrange.mockResolvedValue([]);
      await webPortal.getUserNotifications(42, 5);
      expect(redis.lrange).toHaveBeenCalledWith('notifications:user:42', 0, 4);
    });
  });
});
