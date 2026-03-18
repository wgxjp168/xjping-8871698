package com.ilbuy.common.mybatis.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.core.config.GlobalConfig;
import com.baomidou.mybatisplus.core.incrementer.DefaultIdentifierGenerator;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.BlockAttackInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.OptimisticLockerInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import com.ilbuy.common.mybatis.handler.MetaObjectFillHandler;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * MyBatis-Plus 核心配置
 *
 * <ul>
 *   <li>分页插件（MySQL 方言，单页最大 500 条）</li>
 *   <li>乐观锁插件</li>
 *   <li>防全表更新/删除插件</li>
 *   <li>字段自动填充</li>
 *   <li>雪花 ID 生成器</li>
 * </ul>
 */
@Configuration
@EnableTransactionManagement
public class MybatisPlusConfig {

    /**
     * MyBatis-Plus 插件链（顺序重要：分页 → 乐观锁 → 防攻击）
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        // 1. 分页插件（MySQL 方言，单页最大 500）
        PaginationInnerInterceptor pagination = new PaginationInnerInterceptor(DbType.MYSQL);
        pagination.setMaxLimit(500L);
        pagination.setOverflow(false); // 超出总页数时不查最后一页，返回空
        interceptor.addInnerInterceptor(pagination);

        // 2. 乐观锁插件
        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());

        // 3. 防全表更新/删除（生产环境保护）
        interceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());

        return interceptor;
    }

    /**
     * 全局配置（字段自动填充）
     */
    @Bean
    @ConditionalOnMissingBean(GlobalConfig.class)
    public GlobalConfig globalConfig(MetaObjectFillHandler fillHandler) {
        GlobalConfig config = new GlobalConfig();
        config.setMetaObjectHandler(fillHandler);
        return config;
    }

    /**
     * 雪花 ID 生成器（workerId 从环境变量取，默认 1）
     */
    @Bean
    @ConditionalOnMissingBean(DefaultIdentifierGenerator.class)
    public DefaultIdentifierGenerator identifierGenerator() {
        long workerId   = Long.parseLong(System.getProperty("snowflake.worker-id",  "1"));
        long datacenterId = Long.parseLong(System.getProperty("snowflake.datacenter-id", "1"));
        return new DefaultIdentifierGenerator(workerId, datacenterId);
    }
}
