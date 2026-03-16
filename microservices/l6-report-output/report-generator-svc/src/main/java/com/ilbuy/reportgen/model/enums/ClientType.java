package com.ilbuy.reportgen.model.enums;

/**
 * Determines which report template to use.
 * B2B              – enterprise procurement report
 * B2C_DEFINED      – consumer, brand already selected
 * B2C_UNDEFINED    – consumer, brand discovery mode
 */
public enum ClientType {
    B2B,
    B2C_DEFINED,
    B2C_UNDEFINED
}
