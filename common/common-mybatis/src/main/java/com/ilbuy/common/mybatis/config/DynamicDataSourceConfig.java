package com.ilbuy.common.mybatis.config;

import com.baomidou.dynamic.datasource.DynamicRoutingDataSource;
import com.baomidou.dynamic.datasource.provider.AbstractDataSourceProvider;
import com.baomidou.dynamic.datasource.provider.DynamicDataSourceProvider;
import com.baomidou.dynamic.datasource.spring.boot.autoconfigure.DataSourceProperty;
import com.baomidou.dynamic.datasource.spring.boot.autoconfigure.DynamicDataSourceAutoConfiguration;
import com.baomidou.dynamic.datasource.spring.boot.autoconfigure.DynamicDataSourceProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.AutoConfigureBefore;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;
import java.util.Map;

/**
 * 动态多数据源配置
 *
 * <p>基于 baomidou dynamic-datasource-spring-boot-starter 实现。</p>
 *
 * <p>application.yml 配置示例：</p>
 * <pre>
 * spring:
 *   datasource:
 *     dynamic:
 *       primary: master          # 默认数据源名称
 *       strict: false            # 未匹配时不抛异常（降级到 primary）
 *       p6spy: true              # 开启 P6spy SQL 监控（开发/测试环境）
 *       druid:                   # 全局 Druid 连接池配置
 *         initial-size: 5
 *         min-idle: 5
 *         max-active: 20
 *         max-wait: 60000
 *         validation-query: SELECT 1
 *       datasource:
 *         master:
 *           url: jdbc:mysql://mysql-master:3306/ilbuy?useSSL=false&serverTimezone=Asia/Shanghai
 *           username: ilbuy
 *           password: ${DB_PASSWORD}
 *           driver-class-name: com.mysql.cj.jdbc.Driver
 *         slave:
 *           url: jdbc:mysql://mysql-slave:3306/ilbuy?useSSL=false&serverTimezone=Asia/Shanghai
 *           username: ilbuy_readonly
 *           password: ${DB_SLAVE_PASSWORD}
 *           driver-class-name: com.mysql.cj.jdbc.Driver
 *         order_ds:
 *           url: jdbc:mysql://mysql-order:3306/ilbuy_order?...
 *           username: order_user
 *           password: ${ORDER_DB_PASSWORD}
 *           driver-class-name: com.mysql.cj.jdbc.Driver
 * </pre>
 *
 * <p>使用方式：</p>
 * <pre>{@code
 * // 方法级切换数据源
 * @DS("slave")   // 读操作走从库
 * public List<UserDO> list() { ... }
 *
 * @DS("order_ds")  // 切换到订单库
 * public void createOrder(OrderDO order) { ... }
 *
 * // 语义化注解（来自 common-mybatis）
 * @ReadOnly        // 等同于 @DS("slave")
 * public UserVO getUser(Long id) { ... }
 * }</pre>
 */
@Slf4j
@Configuration
@RequiredArgsConstructor
@AutoConfigureBefore(DynamicDataSourceAutoConfiguration.class)
@ConditionalOnProperty(
        prefix = "spring.datasource.dynamic",
        name   = "enabled",
        havingValue = "true",
        matchIfMissing = true
)
public class DynamicDataSourceConfig {

    private final DynamicDataSourceProperties properties;

    /**
     * 自定义数据源提供者（可扩展：从 Nacos/DB 读取数据源配置）
     *
     * <p>默认使用 YML 静态配置，如需从 Nacos 动态获取，
     * 继承 {@link AbstractDataSourceProvider} 覆盖此 Bean。</p>
     */
    @Bean
    @Primary
    public DynamicDataSourceProvider dynamicDataSourceProvider() {
        Map<String, DataSourceProperty> datasourceMap = properties.getDatasource();
        log.info("[DynamicDataSource] 加载数据源配置，共 {} 个: {}",
                datasourceMap.size(), datasourceMap.keySet());

        return new AbstractDataSourceProvider() {
            @Override
            public Map<String, DataSource> loadDataSources() {
                // 调用框架内置的连接池创建逻辑（Druid / HikariCP）
                return createDataSourceMap(datasourceMap);
            }
        };
    }
}
