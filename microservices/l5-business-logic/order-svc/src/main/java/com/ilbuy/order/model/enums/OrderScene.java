package com.ilbuy.order.model.enums;

/**
 * 订单业务场景
 *
 * B2B — 企业采购订单：支持合同关联、增值税专票申请、最低起订量校验、账期付款。
 * B2C — 消费者订单：支持优惠券、闪购价、即时支付。
 */
public enum OrderScene {
    B2B,
    B2C
}
