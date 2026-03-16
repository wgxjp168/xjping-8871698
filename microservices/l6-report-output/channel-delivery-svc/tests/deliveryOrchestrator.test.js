'use strict';

jest.mock('../src/config/database', () => ({
  migrate: { latest: jest.fn().mockResolvedValue() },
  raw: jest.fn().mockResolvedValue([]),
  fn: { now: () => new Date() },
}));

jest.mock('../src/config/redis', () => ({
  on: jest.fn(), ping: jest.fn(), lpush: jest.fn(), ltrim: jest.fn(),
  expire: jest.fn(), publish: jest.fn(), hset: jest.fn(), hgetall: jest.fn(),
  get: jest.fn(), setex: jest.fn(), lrange: jest.fn(),
}));

jest.mock('../src/models/DeliveryTask');
jest.mock('../src/services/emailService');
jest.mock('../src/services/wechatService');
jest.mock('../src/services/appPushService');
jest.mock('../src/services/webPortalService');

const DeliveryTask      = require('../src/models/DeliveryTask');
const emailService      = require('../src/services/emailService');
const wechatService     = require('../src/services/wechatService');
const appPushService    = require('../src/services/appPushService');
const webPortalService  = require('../src/services/webPortalService');
const orchestrator      = require('../src/services/deliveryOrchestrator');

describe('DeliveryOrchestrator', () => {
  const basePayload = {
    formatJobNo: 'FMT-TEST001',
    l5ReportNo: 'RPT-TEST-001',
    userId: 100,
    reportTitle: 'Test Report',
    clientType: 'B2B',
    htmlUrl: 'http://minio/test.html',
    pdfUrl: 'http://minio/test.pdf',
    excelUrl: 'http://minio/test.xlsx',
    deliverWeb: true,
    deliverEmail: false,
    deliverWechat: false,
    deliverApp: false,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    DeliveryTask.findByFormatJobNo.mockResolvedValue(null);
    DeliveryTask.create.mockResolvedValue({ id: 1, delivery_no: 'DEL-TEST001' });
    DeliveryTask.logChannel.mockResolvedValue({});
    DeliveryTask.complete.mockResolvedValue(1);
    webPortalService.notifyReportReady.mockResolvedValue({ notificationStored: true });
  });

  test('creates delivery task and completes web delivery', async () => {
    const result = await orchestrator.orchestrate(basePayload);

    expect(DeliveryTask.create).toHaveBeenCalledTimes(1);
    expect(webPortalService.notifyReportReady).toHaveBeenCalledWith(
      expect.objectContaining({ userId: 100, l5ReportNo: 'RPT-TEST-001' })
    );
    expect(DeliveryTask.complete).toHaveBeenCalledTimes(1);
  });

  test('sends email when deliverEmail=true', async () => {
    emailService.sendReportEmail.mockResolvedValue({ messageId: 'msg-123' });

    await orchestrator.orchestrate({
      ...basePayload,
      deliverEmail: true,
      emailAddress: 'test@corp.com',
    });

    expect(emailService.sendReportEmail).toHaveBeenCalledWith(
      expect.objectContaining({ to: 'test@corp.com' })
    );
  });

  test('sends wechat when deliverWechat=true', async () => {
    wechatService.sendTemplateMessage.mockResolvedValue({ msgid: 999 });

    await orchestrator.orchestrate({
      ...basePayload,
      deliverWechat: true,
      wechatOpenId: 'oXXXXXXtest',
    });

    expect(wechatService.sendTemplateMessage).toHaveBeenCalledWith(
      expect.objectContaining({ openId: 'oXXXXXXtest' })
    );
  });

  test('skips duplicate delivery (idempotency)', async () => {
    DeliveryTask.findByFormatJobNo.mockResolvedValue({ id: 1, delivery_no: 'DEL-EXISTING' });

    const result = await orchestrator.orchestrate(basePayload);

    expect(DeliveryTask.create).not.toHaveBeenCalled();
    expect(result.delivery_no).toBe('DEL-EXISTING');
  });

  test('handles channel failure gracefully (partial success)', async () => {
    emailService.sendReportEmail.mockRejectedValue(new Error('SMTP timeout'));

    const result = await orchestrator.orchestrate({
      ...basePayload,
      deliverEmail: true,
      emailAddress: 'fail@corp.com',
    });

    // Should still complete (partial)
    expect(DeliveryTask.complete).toHaveBeenCalledTimes(1);
    // Channel log should record FAILED for email
    const logCalls = DeliveryTask.logChannel.mock.calls;
    const emailLog = logCalls.find(c => c[0].channel === 'EMAIL');
    expect(emailLog[0].status).toBe('FAILED');
  });
});
