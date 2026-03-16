'use strict';

const axios = require('axios');
const env = require('../config/env');
const logger = require('../config/logger');

/**
 * Mobile App Push Notification Service
 * Sends push notifications via a unified push gateway (supports FCM/APNs).
 * Compatible with UniPush (个推) or custom push gateway.
 */
class AppPushService {

  /**
   * Send push notification to mobile app.
   * @param {object} opts
   * @param {string} opts.deviceToken
   * @param {string} opts.reportTitle
   * @param {string} opts.l5ReportNo
   * @param {string} [opts.htmlUrl]
   * @param {string} [opts.clientType]
   */
  async sendPush(opts) {
    const { deviceToken, reportTitle, l5ReportNo, htmlUrl, clientType } = opts;

    if (!env.PUSH_GATEWAY_URL || !deviceToken) {
      logger.warn('[AppPush] Push gateway not configured or deviceToken missing, skipping');
      return { skipped: true };
    }

    logger.info(`[AppPush] Sending push to token=${deviceToken.substring(0, 8)}..., reportNo=${l5ReportNo}`);

    const payload = {
      token: deviceToken,
      notification: {
        title: '📊 报告生成完毕',
        body:  `《${reportTitle}》已可查看`,
        sound: 'default',
        badge: 1,
      },
      data: {
        type:        'REPORT_READY',
        l5ReportNo,
        htmlUrl:     htmlUrl || '',
        clientType:  clientType || '',
        timestamp:   Date.now().toString(),
      },
      android: {
        priority: 'high',
        channelId: 'report_notifications',
      },
      apns: {
        headers: { 'apns-priority': '10' },
        payload: {
          aps: {
            alert: {
              title: '📊 报告生成完毕',
              body:  `《${reportTitle}》已可查看`,
            },
            sound: 'default',
            badge: 1,
          },
        },
      },
    };

    try {
      const resp = await axios.post(`${env.PUSH_GATEWAY_URL}/v1/push`, payload, {
        headers: {
          'Authorization': `Bearer ${env.PUSH_API_KEY}`,
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      });

      logger.info(`[AppPush] Push sent: status=${resp.status}, data=${JSON.stringify(resp.data)}`);
      return { success: true, response: resp.data };
    } catch (err) {
      logger.error(`[AppPush] Push failed: ${err.message}`);
      throw err;
    }
  }
}

module.exports = new AppPushService();
