package com.health.physical.urine.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

/**
 * 尿机服务配置
 */
@Configuration
public class UrineConfig {

    /**
     * MyBatis-Plus 分页插件（尿机结果分页查询使用）
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        return interceptor;
    }

    /**
     * RestTemplate（同步尿机数据至县域使用）
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
