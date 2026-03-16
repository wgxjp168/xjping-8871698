'use strict';

const request = require('supertest');

// Mock dependencies before requiring app
jest.mock('../src/config/database', () => ({
  migrate: { latest: jest.fn().mockResolvedValue() },
  raw: jest.fn().mockResolvedValue([]),
  fn: { now: () => new Date() },
}));

jest.mock('../src/config/redis', () => ({
  on:        jest.fn(),
  ping:      jest.fn().mockResolvedValue('PONG'),
  lpush:     jest.fn().mockResolvedValue(1),
  ltrim:     jest.fn().mockResolvedValue('OK'),
  expire:    jest.fn().mockResolvedValue(1),
  publish:   jest.fn().mockResolvedValue(0),
  hset:      jest.fn().mockResolvedValue(1),
  hgetall:   jest.fn().mockResolvedValue(null),
  get:       jest.fn().mockResolvedValue(null),
  setex:     jest.fn().mockResolvedValue('OK'),
  lrange:    jest.fn().mockResolvedValue([]),
}));

jest.mock('../src/models/DeliveryTask', () => ({
  create:           jest.fn(),
  findByDeliveryNo: jest.fn(),
  findByFormatJobNo: jest.fn(),
  getChannelLogs:   jest.fn().mockResolvedValue([]),
  logChannel:       jest.fn(),
  complete:         jest.fn(),
  updateStatus:     jest.fn(),
}));

jest.mock('../src/services/emailService',    () => ({ sendReportEmail:      jest.fn().mockResolvedValue({ messageId: 'test-msg-id' }) }));
jest.mock('../src/services/wechatService',   () => ({ sendTemplateMessage:  jest.fn().mockResolvedValue({ msgid: 123 }) }));
jest.mock('../src/services/appPushService',  () => ({ sendPush:             jest.fn().mockResolvedValue({ success: true }) }));

const DeliveryTask = require('../src/models/DeliveryTask');
const app = require('../src/app');

describe('POST /internal/v1/deliveries', () => {
  const validPayload = {
    formatJobNo:  'FMT-ABC123',
    l5ReportNo:   'RPT-20240101-001',
    userId:       100,
    reportTitle:  'Test B2B Report',
    clientType:   'B2B',
    htmlUrl:      'http://minio/reports/test.html',
    pdfUrl:       'http://minio/reports/test.pdf',
    excelUrl:     'http://minio/reports/test.xlsx',
    deliverEmail: true,
    emailAddress: 'test@corp.com',
    deliverWechat: false,
    deliverApp:   false,
    deliverWeb:   true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    DeliveryTask.findByFormatJobNo.mockResolvedValue(null);
    DeliveryTask.create.mockResolvedValue({ id: 1, delivery_no: 'DEL-TEST001', ...validPayload });
  });

  test('returns 202 for valid delivery request', async () => {
    const resp = await request(app)
      .post('/internal/v1/deliveries')
      .send(validPayload)
      .expect(202);

    expect(resp.body.status).toBe('ACCEPTED');
    expect(resp.body.formatJobNo).toBe('FMT-ABC123');
  });

  test('returns 400 for missing required fields', async () => {
    const resp = await request(app)
      .post('/internal/v1/deliveries')
      .send({ formatJobNo: 'FMT-123' }) // missing required fields
      .expect(400);

    expect(resp.body.errors).toBeDefined();
    expect(resp.body.errors.length).toBeGreaterThan(0);
  });

  test('returns 400 for invalid clientType', async () => {
    const resp = await request(app)
      .post('/internal/v1/deliveries')
      .send({ ...validPayload, clientType: 'INVALID' })
      .expect(400);

    expect(resp.body.errors).toBeDefined();
  });
});

describe('GET /internal/v1/deliveries/:deliveryNo', () => {
  test('returns 200 with task and channel logs for existing delivery', async () => {
    DeliveryTask.findByDeliveryNo.mockResolvedValue({
      id: 1, delivery_no: 'DEL-TEST001', status: 'COMPLETED',
    });
    DeliveryTask.getChannelLogs.mockResolvedValue([
      { channel: 'WEB', status: 'SUCCESS' },
      { channel: 'EMAIL', status: 'SUCCESS' },
    ]);

    const resp = await request(app)
      .get('/internal/v1/deliveries/DEL-TEST001')
      .expect(200);

    expect(resp.body.task).toBeDefined();
    expect(resp.body.channelLogs).toHaveLength(2);
  });

  test('returns 404 for unknown delivery', async () => {
    DeliveryTask.findByDeliveryNo.mockResolvedValue(null);
    await request(app).get('/internal/v1/deliveries/DEL-UNKNOWN').expect(404);
  });
});

describe('GET /actuator/health', () => {
  test('returns health status', async () => {
    const resp = await request(app).get('/actuator/health').expect(200);
    expect(resp.body.service).toBe('channel-delivery-svc');
    expect(resp.body.status).toBeDefined();
  });
});

describe('L7/L8 hooks', () => {
  test('monetize-hook returns 202', async () => {
    const resp = await request(app)
      .post('/internal/v1/deliveries/DEL-TEST001/monetize-hook')
      .send({ plan: 'PREMIUM' })
      .expect(202);
    expect(resp.body.status).toBe('RECEIVED');
  });

  test('feedback-hook returns 202', async () => {
    const resp = await request(app)
      .post('/internal/v1/deliveries/DEL-TEST001/feedback-hook')
      .send({ rating: 5, comment: 'Excellent report!' })
      .expect(202);
    expect(resp.body.status).toBe('RECEIVED');
  });
});
