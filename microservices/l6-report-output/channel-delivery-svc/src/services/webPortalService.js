'use strict';

const redis = require('../config/redis');
const logger = require('../config/logger');
const env = require('../config/env');

/**
 * Web Portal Notification Service
 * Stores a notification in Redis that the Web Portal can poll/subscribe.
 * Also supports Server-Sent Events (SSE) by writing to a user-specific channel.
 */
class WebPortalService {

  /**
   * Notify the web portal that a report is ready.
   * @param {object} opts
   * @param {number} opts.userId
   * @param {string} opts.l5ReportNo
   * @param {string} opts.reportTitle
   * @param {string} opts.clientType
   * @param {string} [opts.htmlUrl]
   * @param {string} [opts.pdfUrl]
   * @param {string} [opts.excelUrl]
   */
  async notifyReportReady(opts) {
    const { userId, l5ReportNo, reportTitle, clientType, htmlUrl, pdfUrl, excelUrl } = opts;

    logger.info(`[WebPortal] Notifying userId=${userId}, reportNo=${l5ReportNo}`);

    const notification = {
      type:       'REPORT_READY',
      userId,
      l5ReportNo,
      reportTitle,
      clientType,
      htmlUrl:    htmlUrl  || null,
      pdfUrl:     pdfUrl   || null,
      excelUrl:   excelUrl || null,
      readUrl:    `${env.WEB_PORTAL_URL}/reports/${l5ReportNo}`,
      createdAt:  new Date().toISOString(),
    };

    // 1. Push to user-specific notification list (Redis LIST, max 50 entries)
    const listKey = `notifications:user:${userId}`;
    await redis.lpush(listKey, JSON.stringify(notification));
    await redis.ltrim(listKey, 0, 49);
    await redis.expire(listKey, 7 * 24 * 3600); // 7 days TTL

    // 2. Publish to Pub/Sub channel for real-time SSE/WebSocket delivery
    const pubChannel = `report:ready:user:${userId}`;
    await redis.publish(pubChannel, JSON.stringify(notification));

    // 3. Store per-report access metadata (for access control)
    const reportKey = `report:access:${l5ReportNo}`;
    await redis.hset(reportKey, {
      userId:     userId.toString(),
      htmlUrl:    htmlUrl  || '',
      pdfUrl:     pdfUrl   || '',
      excelUrl:   excelUrl || '',
      createdAt:  new Date().toISOString(),
      expiresAt:  new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
    });
    await redis.expire(reportKey, 72 * 3600);

    logger.info(`[WebPortal] Redis notification stored and published for userId=${userId}`);

    return {
      notificationStored: true,
      pubChannel,
      readUrl: notification.readUrl,
    };
  }

  /**
   * Get unread notifications for a user (for portal API).
   */
  async getUserNotifications(userId, limit = 20) {
    const listKey = `notifications:user:${userId}`;
    const items = await redis.lrange(listKey, 0, limit - 1);
    return items.map(item => JSON.parse(item));
  }

  /**
   * Validate access: check if userId has access to this report.
   */
  async checkAccess(l5ReportNo, userId) {
    const reportKey = `report:access:${l5ReportNo}`;
    const meta = await redis.hgetall(reportKey);
    if (!meta || !meta.userId) return false;
    return meta.userId === userId.toString();
  }
}

module.exports = new WebPortalService();
