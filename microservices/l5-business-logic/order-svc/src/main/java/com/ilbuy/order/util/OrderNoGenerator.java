package com.ilbuy.order.util;

import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 简单的内存自增订单号生成器，生产环境建议换成分布式 ID（Snowflake / Redis INCR）
 * 格式: ORD-YYYYMMDD-XXXXXXXX
 */
@Component
public class OrderNoGenerator {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyyMMdd");
    private final AtomicLong counter = new AtomicLong(System.currentTimeMillis() % 100_000_000L);

    public String next() {
        String date = LocalDate.now().format(FMT);
        long seq  = counter.incrementAndGet() % 100_000_000L;
        return String.format("ORD-%s-%08d", date, seq);
    }
}
