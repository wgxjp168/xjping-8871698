'use strict';

/**
 * L6 channel-delivery-svc DB migration
 */
exports.up = async function (knex) {
  // Delivery tasks table
  await knex.schema.createTable('l6_delivery_tasks', (t) => {
    t.bigIncrements('id').primary();
    t.string('delivery_no', 64).notNullable().unique();
    t.string('format_job_no', 64).notNullable();
    t.string('l5_report_no', 64).notNullable();
    t.bigInteger('user_id').notNullable();
    t.string('report_title', 255).notNullable();
    t.string('client_type', 32).notNullable();
    t.string('html_url', 512);
    t.string('pdf_url', 512);
    t.string('excel_url', 512);
    t.boolean('deliver_web').defaultTo(true);
    t.boolean('deliver_email').defaultTo(false);
    t.string('email_address', 255);
    t.boolean('deliver_wechat').defaultTo(false);
    t.string('wechat_open_id', 128);
    t.boolean('deliver_app').defaultTo(false);
    t.string('app_device_token', 512);
    t.string('status', 32).notNullable().defaultTo('PENDING');
    t.text('error_message');
    t.timestamp('started_at');
    t.timestamp('completed_at');
    t.timestamps(true, true);
  });

  // Per-channel delivery log
  await knex.schema.createTable('l6_channel_logs', (t) => {
    t.bigIncrements('id').primary();
    t.bigInteger('delivery_task_id').notNullable().references('id').inTable('l6_delivery_tasks').onDelete('CASCADE');
    t.string('channel', 32).notNullable();   // WEB | EMAIL | WECHAT | APP
    t.string('status', 32).notNullable();    // SUCCESS | FAILED | SKIPPED
    t.string('recipient', 255);
    t.text('response_data');
    t.text('error_message');
    t.timestamp('delivered_at');
    t.timestamps(true, true);
  });

  // Indexes
  await knex.schema.table('l6_delivery_tasks', (t) => {
    t.index('l5_report_no');
    t.index('user_id');
    t.index('status');
  });

  await knex.schema.table('l6_channel_logs', (t) => {
    t.index('delivery_task_id');
    t.index('channel');
  });
};

exports.down = async function (knex) {
  await knex.schema.dropTableIfExists('l6_channel_logs');
  await knex.schema.dropTableIfExists('l6_delivery_tasks');
};
