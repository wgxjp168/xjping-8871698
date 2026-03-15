package com.ilbuy.datasvc;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * ILbuy L4 数据存储服务
 * <p>
 * 职责：
 * - 接收 L3 ETL 服务推送的清洗后商品数据
 * - 写入 MySQL（主存储）、Redis（热缓存）、ES（全文检索）
 * - MinIO 存储商品图片对象
 * - ClickHouse 写入分析宽表
 * - Canal 监听 MySQL binlog → ES 增量同步
 * - RabbitMQ 异步解耦写入流程
 * - 为 L5 业务层预留统一查询接口
 * </p>
 *
 * @port 8035
 */
@SpringBootApplication
@EnableJpaAuditing
@EnableCaching
@EnableAsync
@EnableScheduling
public class DataSvcApplication {

    public static void main(String[] args) {
        SpringApplication.run(DataSvcApplication.class, args);
    }
}
