package com.ilbuy.common.mybatis.config;

import com.alibaba.druid.pool.DruidDataSource;
import com.alibaba.druid.support.jakarta.StatViewServlet;
import com.alibaba.druid.support.jakarta.WebStatFilter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.boot.web.servlet.ServletRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * Druid 连接池与监控台配置
 *
 * <p>功能：</p>
 * <ul>
 *   <li>连接池核心参数（initialSize/minIdle/maxActive/maxWait）</li>
 *   <li>连接有效性检测（testWhileIdle/validationQuery）</li>
 *   <li>慢 SQL 检测（slowSqlMillis=2000ms）</li>
 *   <li>Druid 监控台（/druid/**）—— 仅开发/测试环境开启</li>
 *   <li>Web 请求统计 Filter</li>
 * </ul>
 *
 * <p>application.yml 激活监控台：</p>
 * <pre>
 * ilbuy:
 *   druid:
 *     monitor:
 *       enabled: true          # false 则不注册 Servlet（生产关闭）
 *       login-username: admin
 *       login-password: ${DRUID_MONITOR_PASSWORD:ilbuy@123}
 * </pre>
 */
@Slf4j
@Configuration
@ConditionalOnClass(DruidDataSource.class)
public class DruidConfig {

    /**
     * Druid 全局连接池参数（可被 application.yml 覆盖）
     */
    @Bean
    @ConfigurationProperties("spring.datasource.druid")
    public DruidDataSource druidDataSource() {
        DruidDataSource ds = new DruidDataSource();
        // 连接池大小
        ds.setInitialSize(5);
        ds.setMinIdle(5);
        ds.setMaxActive(20);
        ds.setMaxWait(60_000);
        // 连接检测
        ds.setTestWhileIdle(true);
        ds.setTestOnBorrow(false);
        ds.setTestOnReturn(false);
        ds.setValidationQuery("SELECT 1");
        ds.setValidationQueryTimeout(3);
        ds.setTimeBetweenEvictionRunsMillis(60_000L);
        ds.setMinEvictableIdleTimeMillis(300_000L);
        // Slow SQL 监控（超过 2 秒记录警告）
        ds.setConnectionProperties("druid.stat.slowSqlMillis=2000;druid.stat.logSlowSql=true");
        // 开启统计和防 SQL 注入 Filter
        try {
            ds.setFilters("stat,wall,slf4j");
        } catch (Exception e) {
            log.warn("[Druid] 设置 Filter 失败: {}", e.getMessage());
        }
        return ds;
    }

    /**
     * Druid 监控台 Servlet（开发/测试环境启用）
     */
    @Bean
    @ConditionalOnProperty(name = "ilbuy.druid.monitor.enabled", havingValue = "true")
    public ServletRegistrationBean<StatViewServlet> druidStatViewServlet() {
        log.info("[Druid] 监控台已启用，路径 /druid/**");
        ServletRegistrationBean<StatViewServlet> bean =
                new ServletRegistrationBean<>(new StatViewServlet(), "/druid/*");
        Map<String, String> params = new HashMap<>();
        params.put("loginUsername", "${ilbuy.druid.monitor.login-username:admin}");
        params.put("loginPassword", "${ilbuy.druid.monitor.login-password:ilbuy@123}");
        params.put("resetEnable",   "false");   // 生产禁止重置统计
        params.put("allow",         "");         // 空=允许所有（生产应设置为内网 IP）
        bean.setInitParameters(params);
        return bean;
    }

    /**
     * Druid Web 请求统计 Filter
     */
    @Bean
    @ConditionalOnProperty(name = "ilbuy.druid.monitor.enabled", havingValue = "true")
    public FilterRegistrationBean<WebStatFilter> druidWebStatFilter() {
        FilterRegistrationBean<WebStatFilter> bean =
                new FilterRegistrationBean<>(new WebStatFilter());
        bean.setUrlPatterns(Arrays.asList("/*"));
        Map<String, String> params = new HashMap<>();
        // 排除静态资源和 Druid 监控路径自身
        params.put("exclusions", "*.js,*.gif,*.jpg,*.png,*.css,*.ico,/druid/*");
        bean.setInitParameters(params);
        return bean;
    }
}
