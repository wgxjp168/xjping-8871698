'use strict';

const axios = require('axios');
const redis = require('../config/redis');
const env = require('../config/env');
const logger = require('../config/logger');

const ACCESS_TOKEN_KEY = 'wechat:access_token';

/**
 * WeChat Official Account (公众号) Delivery Service
 * Sends template message notification when report is ready.
 */
class WechatService {
  constructor() {
    this.appId     = env.WECHAT_APP_ID;
    this.appSecret = env.WECHAT_APP_SECRET;
    this.apiBase   = env.WECHAT_API_BASE;
    this.templateId = env.WECHAT_TEMPLATE_ID;
  }

  /**
   * Get or refresh WeChat access_token (cached in Redis for 7000 seconds).
   */
  async getAccessToken() {
    const cached = await redis.get(ACCESS_TOKEN_KEY);
    if (cached) return cached;

    logger.debug('[WechatService] Fetching new access_token');
    const resp = await axios.get(`${this.apiBase}/cgi-bin/token`, {
      params: {
        grant_type: 'client_credential',
        appid:      this.appId,
        secret:     this.appSecret,
      },
      timeout: 10000,
    });

    if (resp.data.errcode) {
      throw new Error(`WeChat token error: ${resp.data.errmsg}`);
    }

    const token = resp.data.access_token;
    await redis.setex(ACCESS_TOKEN_KEY, 7000, token);
    logger.debug('[WechatService] access_token refreshed');
    return token;
  }

  /**
   * Send template message to a user's openid.
   * @param {object} opts
   * @param {string} opts.openId
   * @param {string} opts.reportTitle
   * @param {string} opts.clientType
   * @param {string} opts.l5ReportNo
   * @param {string} [opts.htmlUrl]
   */
  async sendTemplateMessage(opts) {
    const { openId, reportTitle, clientType, l5ReportNo, htmlUrl } = opts;

    if (!this.appId || !this.appSecret || !openId) {
      logger.warn('[WechatService] WeChat not configured or openId missing, skipping');
      return { skipped: true };
    }

    logger.info(`[WechatService] Sending template to openId=${openId}, reportNo=${l5ReportNo}`);

    const token = await this.getAccessToken();

    const payload = {
      touser:      openId,
      template_id: this.templateId,
      url:         htmlUrl || `${env.WEB_PORTAL_URL}/reports/${l5ReportNo}`,
      miniprogram: {
        appid:    this.appId,
        pagepath: `pages/report/detail?reportNo=${l5ReportNo}`,
      },
      data: {
        first: {
          value: '您的采购报告已生成完毕 🎉',
          color: '#1a56db',
        },
        keyword1: {
          value: reportTitle,
          color: '#1f2937',
        },
        keyword2: {
          value: this.clientTypeLabel(clientType),
          color: '#374151',
        },
        keyword3: {
          value: l5ReportNo,
          color: '#6b7280',
        },
        keyword4: {
          value: new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
          color: '#6b7280',
        },
        remark: {
          value: '点击查看完整报告，链接有效期72小时。',
          color: '#9ca3af',
        },
      },
    };

    const resp = await axios.post(
      `${this.apiBase}/cgi-bin/message/template/send?access_token=${token}`,
      payload,
      { timeout: 10000 }
    );

    if (resp.data.errcode && resp.data.errcode !== 0) {
      throw new Error(`WeChat template send error ${resp.data.errcode}: ${resp.data.errmsg}`);
    }

    logger.info(`[WechatService] Template sent: msgid=${resp.data.msgid}`);
    return { msgid: resp.data.msgid, errcode: resp.data.errcode };
  }

  clientTypeLabel(type) {
    const map = { B2B: 'B2B企业采购', B2C_DEFINED: 'B2C已定品牌', B2C_UNDEFINED: 'B2C品牌发现' };
    return map[type] || type;
  }
}

module.exports = new WechatService();
