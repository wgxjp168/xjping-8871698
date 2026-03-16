'use strict';

const { v4: uuidv4 } = require('uuid');
const DeliveryTask = require('../models/DeliveryTask');
const emailService = require('./emailService');
const wechatService = require('./wechatService');
const appPushService = require('./appPushService');
const webPortalService = require('./webPortalService');
const logger = require('../config/logger');

/**
 * Delivery Orchestrator – coordinates all channel deliveries for a report.
 * Runs channels in parallel, logs each result independently.
 */
class DeliveryOrchestrator {

  /**
   * Main entry point: create delivery task and dispatch to all channels.
   */
  async orchestrate(payload) {
    const {
      formatJobNo, l5ReportNo, userId, reportTitle, clientType,
      htmlUrl, pdfUrl, excelUrl,
      deliverEmail, emailAddress,
      deliverWechat, wechatOpenId,
      deliverApp, appDeviceToken,
    } = payload;

    // Idempotency check
    const existing = await DeliveryTask.findByFormatJobNo(formatJobNo);
    if (existing) {
      logger.warn(`[Orchestrator] Duplicate delivery for formatJobNo=${formatJobNo}`);
      return existing;
    }

    const deliveryNo = `DEL-${uuidv4().replace(/-/g, '').substring(0, 16).toUpperCase()}`;

    const task = await DeliveryTask.create({
      delivery_no:      deliveryNo,
      format_job_no:    formatJobNo,
      l5_report_no:     l5ReportNo,
      user_id:          userId,
      report_title:     reportTitle,
      client_type:      clientType,
      html_url:         htmlUrl || null,
      pdf_url:          pdfUrl  || null,
      excel_url:        excelUrl || null,
      deliver_web:      true,
      deliver_email:    !!deliverEmail,
      email_address:    emailAddress || null,
      deliver_wechat:   !!deliverWechat,
      wechat_open_id:   wechatOpenId || null,
      deliver_app:      !!deliverApp,
      app_device_token: appDeviceToken || null,
      status:           'PROCESSING',
      started_at:       new Date(),
    });

    logger.info(`[Orchestrator] Delivery task created: ${deliveryNo} for userId=${userId}`);

    // Dispatch all channels concurrently
    const channelPromises = [];

    // 1. Web Portal (always)
    channelPromises.push(
      this.deliverToChannel(task.id, 'WEB', userId.toString(), async () => {
        return webPortalService.notifyReportReady({
          userId, l5ReportNo, reportTitle, clientType, htmlUrl, pdfUrl, excelUrl,
        });
      })
    );

    // 2. Email
    if (deliverEmail && emailAddress) {
      channelPromises.push(
        this.deliverToChannel(task.id, 'EMAIL', emailAddress, async () => {
          return emailService.sendReportEmail({
            to: emailAddress, reportTitle, clientType, htmlUrl, pdfUrl, excelUrl, l5ReportNo,
          });
        })
      );
    }

    // 3. WeChat
    if (deliverWechat && wechatOpenId) {
      channelPromises.push(
        this.deliverToChannel(task.id, 'WECHAT', wechatOpenId, async () => {
          return wechatService.sendTemplateMessage({
            openId: wechatOpenId, reportTitle, clientType, l5ReportNo, htmlUrl,
          });
        })
      );
    }

    // 4. Mobile App Push
    if (deliverApp && appDeviceToken) {
      channelPromises.push(
        this.deliverToChannel(task.id, 'APP', appDeviceToken.substring(0, 12) + '...', async () => {
          return appPushService.sendPush({
            deviceToken: appDeviceToken, reportTitle, l5ReportNo, htmlUrl, clientType,
          });
        })
      );
    }

    // Wait for all channels (errors per channel are logged, not re-thrown)
    const results = await Promise.allSettled(channelPromises);
    const allSuccess = results.every(r => r.status === 'fulfilled');

    await DeliveryTask.complete(task.id, {
      status: allSuccess ? 'COMPLETED' : 'PARTIAL',
    });

    logger.info(`[Orchestrator] Delivery ${deliveryNo} finished. allSuccess=${allSuccess}`);
    return { deliveryNo, results: results.length, allSuccess };
  }

  /**
   * Wrap a channel delivery, catching errors and logging the result.
   */
  async deliverToChannel(taskId, channel, recipient, fn) {
    const start = Date.now();
    try {
      const result = await fn();
      const skipped = result && result.skipped;

      await DeliveryTask.logChannel({
        delivery_task_id: taskId,
        channel,
        status:           skipped ? 'SKIPPED' : 'SUCCESS',
        recipient,
        response_data:    JSON.stringify(result),
      });

      logger.info(`[Orchestrator] Channel ${channel} → ${skipped ? 'SKIPPED' : 'SUCCESS'} (${Date.now() - start}ms)`);
      return { channel, status: 'SUCCESS' };
    } catch (err) {
      logger.error(`[Orchestrator] Channel ${channel} FAILED: ${err.message}`);

      await DeliveryTask.logChannel({
        delivery_task_id: taskId,
        channel,
        status:           'FAILED',
        recipient,
        error_message:    err.message,
      });

      return { channel, status: 'FAILED', error: err.message };
    }
  }
}

module.exports = new DeliveryOrchestrator();
