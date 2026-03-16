'use strict';

const nodemailer = require('nodemailer');
const env = require('../config/env');
const logger = require('../config/logger');

/**
 * Email Channel Delivery Service
 * Sends a styled HTML email with report download links to the report owner.
 *
 * SMTP configuration:
 *  - Port 465 → implicit TLS (EMAIL_SECURE=true)
 *  - Port 587 → STARTTLS (EMAIL_SECURE=false + requireTLS:true)
 *  - Port 25  → unencrypted relay (dev/testing only)
 */
class EmailService {
  constructor() {
    const port   = env.EMAIL_PORT;
    const secure = env.EMAIL_SECURE;  // true only for port 465 implicit TLS

    this.transporter = nodemailer.createTransport({
      host:       env.EMAIL_HOST,
      port,
      secure,
      // STARTTLS upgrade for port 587
      requireTLS: !secure && port === 587,
      auth: {
        user: env.EMAIL_USER,
        pass: env.EMAIL_PASS,
      },
      pool:           true,
      maxConnections: 5,
      maxMessages:    100,
      rateDelta:      1000,
      rateLimit:      20,
      // Reject self-signed certs in prod; allow in dev
      tls: {
        rejectUnauthorized: process.env.NODE_ENV === 'production',
      },
    });
  }

  /**
   * Send report delivery email.
   * @param {object} opts
   * @param {string} opts.to            Recipient email
   * @param {string} opts.reportTitle   Report display title
   * @param {string} opts.clientType    B2B | B2C_DEFINED | B2C_UNDEFINED
   * @param {string} [opts.htmlUrl]     Pre-signed URL to HTML report
   * @param {string} [opts.pdfUrl]      Pre-signed URL to PDF
   * @param {string} [opts.excelUrl]    Pre-signed URL to Excel
   * @param {string} opts.l5ReportNo    Report number for reference
   */
  async sendReportEmail(opts) {
    const { to, reportTitle, clientType, htmlUrl, pdfUrl, excelUrl, l5ReportNo } = opts;

    logger.info(`[EmailService] Sending report email → ${to}, reportNo=${l5ReportNo}`);

    const subject = `📊 您的${this.clientTypeLabel(clientType)}报告已生成 — ${reportTitle}`;

    const result = await this.transporter.sendMail({
      from:    env.EMAIL_FROM,
      to,
      subject,
      html:    this.buildEmailHtml(opts),
      text:    this.buildEmailText(opts),
      headers: {
        'X-Report-No':     l5ReportNo,
        'X-Client-Type':   clientType,
        'X-Mailer':        'ILbuy Report Platform v1.0',
      },
    });

    logger.info(`[EmailService] Email sent: messageId=${result.messageId}, accepted=${result.accepted}`);
    return { messageId: result.messageId, accepted: result.accepted };
  }

  buildEmailText({ reportTitle, l5ReportNo, htmlUrl, pdfUrl, excelUrl }) {
    return [
      `您好，`,
      ``,
      `您请求的报告《${reportTitle}》已生成完毕。`,
      ``,
      `报告编号：${l5ReportNo}`,
      htmlUrl  ? `在线浏览：${htmlUrl}` : '',
      pdfUrl   ? `PDF下载：${pdfUrl}` : '',
      excelUrl ? `Excel下载：${excelUrl}` : '',
      ``,
      `链接有效期72小时，请及时保存。`,
      ``,
      `我来购ILbuy智能采购平台`,
    ].filter(line => line !== undefined).join('\n');
  }

  buildEmailHtml({ reportTitle, clientType, htmlUrl, pdfUrl, excelUrl, l5ReportNo }) {
    const btnBase = `display:inline-block;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px;margin:6px 8px 6px 0;`;

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>报告已生成 — 我来购ILbuy</title>
</head>
<body style="margin:0;padding:0;background:#f8f9fc;font-family:'Helvetica Neue',Arial,'PingFang SC',sans-serif;color:#1f2937;">
<table width="100%" cellpadding="0" cellspacing="0" role="presentation">
  <tr><td align="center" style="padding:40px 20px;">
    <table width="600" cellpadding="0" cellspacing="0" role="presentation"
           style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">

      <!-- Header -->
      <tr><td style="background:#1a56db;padding:32px 40px;">
        <p style="margin:0 0 6px;color:rgba(255,255,255,.7);font-size:13px;">我来购 ILbuy · 智能采购报告平台</p>
        <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">您的报告已生成完毕</h1>
        <p style="margin:8px 0 0;color:rgba(255,255,255,.8);font-size:14px;">${this.clientTypeLabel(clientType)}</p>
      </td></tr>

      <!-- Body -->
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 20px;font-size:15px;color:#374151;">您好，</p>
        <p style="margin:0 0 16px;font-size:15px;color:#374151;">
          您请求的报告已生成，可通过以下方式查看和下载：
        </p>

        <!-- Report Info Card -->
        <div style="background:#f0f4ff;border-radius:8px;padding:20px;margin:20px 0;">
          <p style="margin:0 0 6px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;">报告信息</p>
          <p style="margin:0;font-size:17px;font-weight:700;color:#1f2937;">${reportTitle}</p>
          <p style="margin:6px 0 0;font-size:12px;color:#9ca3af;">编号：${l5ReportNo}</p>
        </div>

        <!-- Download Buttons -->
        <div style="margin:24px 0;">
          ${htmlUrl  ? `<a href="${htmlUrl}"  style="${btnBase}background:#1a56db;color:#fff;">🌐 在线浏览报告</a>` : ''}
          ${pdfUrl   ? `<a href="${pdfUrl}"   style="${btnBase}background:#fff;color:#1a56db;border:2px solid #1a56db;">📄 下载PDF</a>` : ''}
          ${excelUrl ? `<a href="${excelUrl}" style="${btnBase}background:#fff;color:#059669;border:2px solid #059669;">📊 下载Excel数据</a>` : ''}
        </div>

        <!-- Expiry Notice -->
        <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:14px;margin-top:20px;">
          <p style="margin:0;font-size:13px;color:#92400e;">
            ⚠️ 下载链接有效期 <strong>72小时</strong>，请及时保存报告。如需重新获取，请登录平台查看。
          </p>
        </div>
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#f8f9fc;padding:20px 40px;border-top:1px solid #e5e7eb;">
        <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;line-height:1.6;">
          此邮件由 <strong>我来购ILbuy智能采购平台</strong> 自动发送，请勿直接回复<br/>
          如有问题，请访问 <a href="https://app.ilbuy.com" style="color:#1a56db;">app.ilbuy.com</a> 或联系客服<br/>
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
    const map = {
      B2B:           'B2B企业采购',
      B2C_DEFINED:   'B2C品牌深度',
      B2C_UNDEFINED: 'B2C品牌发现',
    };
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

  closeConnections() {
    this.transporter.close();
  }
}

module.exports = new EmailService();
