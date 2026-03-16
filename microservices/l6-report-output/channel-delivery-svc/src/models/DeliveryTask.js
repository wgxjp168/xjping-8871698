'use strict';

const db = require('../config/database');

const TABLE = 'l6_delivery_tasks';
const LOG_TABLE = 'l6_channel_logs';

class DeliveryTask {

  static async create(data) {
    const [row] = await db(TABLE).insert(data).returning('*');
    return row;
  }

  static async findById(id) {
    return db(TABLE).where({ id }).first();
  }

  static async findByDeliveryNo(deliveryNo) {
    return db(TABLE).where({ delivery_no: deliveryNo }).first();
  }

  static async findByFormatJobNo(formatJobNo) {
    return db(TABLE).where({ format_job_no: formatJobNo }).first();
  }

  static async findByUserId(userId) {
    return db(TABLE).where({ user_id: userId }).orderBy('created_at', 'desc');
  }

  static async updateStatus(id, status, errorMessage = null) {
    return db(TABLE).where({ id }).update({
      status,
      error_message: errorMessage,
      updated_at: db.fn.now(),
    });
  }

  static async complete(id, extra = {}) {
    return db(TABLE).where({ id }).update({
      status: 'COMPLETED',
      completed_at: db.fn.now(),
      updated_at: db.fn.now(),
      ...extra,
    });
  }

  static async logChannel(data) {
    const [row] = await db(LOG_TABLE).insert({
      ...data,
      delivered_at: db.fn.now(),
    }).returning('*');
    return row;
  }

  static async getChannelLogs(deliveryTaskId) {
    return db(LOG_TABLE).where({ delivery_task_id: deliveryTaskId }).orderBy('created_at');
  }
}

module.exports = DeliveryTask;
