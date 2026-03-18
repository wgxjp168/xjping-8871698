package com.ilbuy.common.mybatis.datasource;

/**
 * 数据源类型枚举
 * <p>配合 @DS 注解和 DynamicDataSourceConfig 使用</p>
 */
public interface DataSourceType {

    /** 主库（读写） */
    String MASTER = "master";

    /** 从库（只读） */
    String SLAVE = "slave";

    /** 订单库 */
    String ORDER = "order_ds";

    /** 用户库 */
    String USER = "user_ds";

    /** 报表库（只读，独立实例） */
    String REPORT = "report_ds";
}
