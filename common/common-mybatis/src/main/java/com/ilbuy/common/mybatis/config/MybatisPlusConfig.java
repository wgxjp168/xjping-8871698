package com.ilbuy.common.mybatis.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.BlockAttackInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.OptimisticLockerInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import com.ilbuy.common.mybatis.handler.MetaObjectHandlerImpl;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * MyBatis-Plus 全局配置
 *
 * <p>包含：
 * <ul>
 *   <li>分页插件（MySQL模式，最大单页1000条）</li>
 *   <li>乐观锁插件（@Version注解支持）</li>
 *   <li>防全表更新/删除插件（生产安全）</li>
 *   <li>字段自动填充处理器</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@AutoConfiguration
@EnableTransactionManagement
public class MybatisPlusConfig {

    /**
     * MyBatis-Plus 拦截器链
     *
     * <p>注意：拦截器顺序重要，分页必须在最前面
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        // 1. 分页插件（MySQL模式）
        PaginationInnerInterceptor paginationInterceptor = new PaginationInnerInterceptor(DbType.MYSQL);
        paginationInterceptor.setMaxLimit(1000L);       // 最大单页1000条
        paginationInterceptor.setOverflow(false);       // 超出最大页不溢出
        interceptor.addInnerInterceptor(paginationInterceptor);

        // 2. 乐观锁插件（支持@Version注解）
        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());

        // 3. 防全表更新/删除插件（生产安全，防止误操作 update table set ...无where条件）
        interceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());

        return interceptor;
    }

    /**
     * 字段自动填充处理器（createTime/updateTime）
     */
    @Bean
    public MetaObjectHandler metaObjectHandler() {
        return new MetaObjectHandlerImpl();
    }
}
