'use strict';

const nodemailer = require('nodemailer');
const env = require('../config/env');
const logger = require('../config/logger');

/**
 * Email Channel Delivery Service
 * Sends styled HTML email with report download links.
 */
class EmailService {
  constructor() {
    this.transporter = nodemailer.createTransport({
      host:   env.EMAIL_HOST,
      port:   env.EMAIL_PORT,
      secure: env.EMAIL_SECURE,
      auth:   {
        user: env.EMAIL_USER,
        pass: env.EMAIL_PASS,
      },
      pool: true,
      maxConnections: 5,
    });
  }

  /**
   * Send report delivery email.
   * @param {object} opts
   * @param {string} opts.to
   * @param {string} opts.reportTitle
   * @param {string} opts.clientType
   * @param {string} [opts.htmlUrl]
   * @param {string} [opts.pdfUrl]
   * @param {string} [opts.excelUrl]
   * @param {string} [opts.l5ReportNo]
   */
  async sendReportEmail(opts) {
    const { to, reportTitle, clientType, htmlUrl, pdfUrl, excelUrl, l5ReportNo } = opts;

    logger.info(`[EmailService] Sending report email to ${to}, reportNo=${l5ReportNo}`);

    const subject = `📊 您的${this.clientTypeLabel(clientType)}报告已生成 — ${reportTitle}`;
    const html = this.buildEmailHtml(opts);

    const info = await this.transporter.sendMail({
      from:    env.EMAIL_FROM,
      to,
      subject,
      html,
      // Fallback plain text
      text: `您好，您请求的报告《${reportTitle}》已生成完毕。\n\n` +
            `报告编号：${l5ReportNo}\n` +
            (htmlUrl ? `在线浏览：${htmlUrl}\n` : '') +
            (pdfUrl  ? `PDF下载：${pdfUrl}\n`  : '') +
            (excelUrl ? `Excel下载：${excelUrl}\n` : '') +
            `\n链接有效期72小时。\n\n我来购ILbuy智能采购平台`,
    });

    logger.info(`[EmailService] Email sent: messageId=${info.messageId}`);
    return { messageId: info.messageId, accepted: info.accepted };
  }

  buildEmailHtml({ reportTitle, clientType, htmlUrl, pdfUrl, excelUrl, l5ReportNo }) {
    const btnStyle = `
      display: inline-block;
      padding: 12px 24px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 600;
      font-size: 14px;
      margin: 6px 8px 6px 0;
    `;

    return `
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#f8f9fc;font-family:'Helvetica Neue',Arial,'PingFang SC',sans-serif;color:#1f2937;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr><td style="background:#1a56db;padding:32px 40px;">
          <p style="margin:0;color:rgba(255,255,255,.7);font-size:13px;">我来购 ILbuy · 智能采购报告平台</p>
          <h1 style="margin:8px 0 0;color:#fff;font-size:22px;font-weight:700;">您的报告已生成</h1>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 16px;font-size:16px;">您好，</p>
          <p style="margin:0 0 16px;font-size:15px;color:#374151;">
            您请求的 <strong style="color:#1a56db;">${this.clientTypeLabel(clientType)}</strong> 报告已生成完毕，请通过以下方式查看：
          </p>
          <div style="background:#f0f4ff;border-radius:8px;padding:20px;margin:20px 0;">
            <p style="margin:0 0 8px;font-size:13px;color:#6b7280;">报告信息</p>
            <p style="margin:0;font-size:16px;font-weight:600;">${reportTitle}</p>
            <p style="margin:4px 0 0;font-size:12px;color:#9ca3af;">编号：${l5ReportNo}</p>
          </div>
          <!-- Download buttons -->
          <div style="margin:24px 0;">
            ${htmlUrl ? `<a href="${htmlUrl}" style="${btnStyle}background:#1a56db;color:#fff;">🌐 在线浏览报告</a>` : ''}
            ${pdfUrl  ? `<a href="${pdfUrl}"  style="${btnStyle}background:#fff;color:#1a56db;border:2px solid #1a56db;">📄 下载PDF</a>`  : ''}
            ${excelUrl ? `<a href="${excelUrl}" style="${btnStyle}background:#fff;color:#059669;border:2px solid #059669;">📊 下载Excel数据</a>` : ''}
          </div>
          <p style="font-size:13px;color:#9ca3af;margin:24px 0 0;">
            ⚠️ 以上链接有效期为 <strong>72小时</strong>，请及时下载保存。
          </p>
        </td></tr>
        <!-- Footer -->
        <tr><td style="background:#f8f9fc;padding:20px 40px;border-top:1px solid #e5e7eb;">
          <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;">
            此邮件由 我来购ILbuy 系统自动发送，请勿直接回复<br/>
            © 2024 ILbuy All Rights Reserved
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
  }

  clientTypeLabel(type) {
    const map = { B2B: 'B2B企业采购', B2C_DEFINED: 'B2C已定品牌', B2C_UNDEFINED: 'B2C品牌发现' };
    return map[type] || type;
  }

  async verifyConnection() {
    try {
      await this.transporter.verify();
      logger.info('[EmailService] SMTP connection verified');
      return true;
    } catch (err) {
      logger.warn('[EmailService] SMTP not available:', err.message);
      return false;
    }
  }
}

module.exports = new EmailService();
