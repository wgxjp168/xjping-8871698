package com.ilbuy.datasvc.config;

import com.clickhouse.jdbc.ClickHouseDataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import java.sql.SQLException;
import java.util.Properties;

/**
 * ClickHouse JDBC 数据源配置
 * 与 MySQL 数据源隔离，使用独立 JdbcTemplate bean: clickhouseJdbcTemplate
 */
@Configuration
public class ClickHouseConfig {

    @Value("${ilbuy.clickhouse.url:jdbc:clickhouse://clickhouse:8123/ilbuy_analytics}")
    private String url;

    @Value("${ilbuy.clickhouse.username:default}")
    private String username;

    @Value("${ilbuy.clickhouse.password:}")
    private String password;

    @Bean(name = "clickhouseDataSource")
    public DataSource clickhouseDataSource() throws SQLException {
        Properties props = new Properties();
        props.setProperty("user", username);
        props.setProperty("password", password);
        props.setProperty("socket_timeout", "30000");
        props.setProperty("connection_timeout", "5000");
        return new ClickHouseDataSource(url, props);
    }

    @Bean(name = "clickhouseJdbcTemplate")
    public JdbcTemplate clickhouseJdbcTemplate(
            @Qualifier("clickhouseDataSource") DataSource ds) {
        return new JdbcTemplate(ds);
    }
}
