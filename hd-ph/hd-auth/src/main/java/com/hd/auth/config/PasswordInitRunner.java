package com.hd.auth.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * 启动时检查并修复 sys_user 表中所有用户的密码 hash。
 * 如果存储的 hash 无法通过 BCrypt 校验（说明 hash 是错误的），
 * 则重新编码默认密码 hd2024 并更新数据库。
 * 正式上线后可删除此类。
 */
@Component
public class PasswordInitRunner implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(PasswordInitRunner.class);
    private static final String DEFAULT_PASSWORD = "hd2024";

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        String correctHash = passwordEncoder.encode(DEFAULT_PASSWORD);
        log.info("=== 密码初始化检查 ===");
        log.info("hd2024 正确 BCrypt hash: {}", correctHash);

        List<Map<String, Object>> users = jdbcTemplate.queryForList(
                "SELECT id, username, password FROM sys_user WHERE deleted = 0");

        if (users.isEmpty()) {
            log.warn("sys_user 表无数据，请先导入 SQL 初始化脚本！");
            return;
        }

        int fixed = 0;
        for (Map<String, Object> user : users) {
            String storedHash = (String) user.get("password");
            boolean matches = false;
            try {
                matches = passwordEncoder.matches(DEFAULT_PASSWORD, storedHash);
            } catch (Exception e) {
                log.warn("用户[{}] 密码 hash 格式异常: {}", user.get("username"), e.getMessage());
            }
            if (!matches) {
                jdbcTemplate.update("UPDATE sys_user SET password = ? WHERE id = ?",
                        correctHash, user.get("id"));
                log.info("已修复用户[{}]的密码 hash", user.get("username"));
                fixed++;
            }
        }

        if (fixed > 0) {
            log.info("=== 共修复 {} 个用户密码，现在可以用 hd2024 登录 ===", fixed);
        } else {
            log.info("=== 所有用户密码 hash 正常 ===");
        }
    }
}
