package com.ilbuy.common.core.utils;

import lombok.extern.slf4j.Slf4j;

/**
 * 雪花算法ID生成器（Snowflake）
 *
 * <p>64位ID结构：
 * <pre>
 * 符号位(1) | 时间戳差(41) | 数据中心ID(5) | 机器ID(5) | 序列号(12)
 * </pre>
 *
 * <p>特点：
 * <ul>
 *   <li>全局唯一、有序递增</li>
 *   <li>每毫秒可生成4096个ID</li>
 *   <li>支持约69年使用寿命（从2024年起）</li>
 * </ul>
 *
 * <p>使用方式：
 * <pre>{@code
 * // 使用默认单例
 * long id = IdGenerator.nextId();
 * String strId = IdGenerator.nextStrId();
 * }</pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
public class IdGenerator {

    /** 起始时间戳（2024-01-01 00:00:00 UTC）*/
    private static final long EPOCH = 1704067200000L;

    /** 机器ID所占位数 */
    private static final long WORKER_ID_BITS = 5L;
    /** 数据中心ID所占位数 */
    private static final long DATA_CENTER_ID_BITS = 5L;
    /** 序列号所占位数 */
    private static final long SEQUENCE_BITS = 12L;

    /** 最大机器ID：31 */
    private static final long MAX_WORKER_ID = ~(-1L << WORKER_ID_BITS);
    /** 最大数据中心ID：31 */
    private static final long MAX_DATA_CENTER_ID = ~(-1L << DATA_CENTER_ID_BITS);

    /** 机器ID移位 */
    private static final long WORKER_ID_SHIFT = SEQUENCE_BITS;
    /** 数据中心ID移位 */
    private static final long DATA_CENTER_ID_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS;
    /** 时间戳移位 */
    private static final long TIMESTAMP_LEFT_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS + DATA_CENTER_ID_BITS;

    /** 序列号掩码（4095）*/
    private static final long SEQUENCE_MASK = ~(-1L << SEQUENCE_BITS);

    private final long workerId;
    private final long dataCenterId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    /** 默认单例（机器ID=1，数据中心ID=1）*/
    private static final IdGenerator DEFAULT_INSTANCE = new IdGenerator(1, 1);

    public IdGenerator(long workerId, long dataCenterId) {
        if (workerId > MAX_WORKER_ID || workerId < 0) {
            throw new IllegalArgumentException(
                    String.format("机器ID必须在0-%d之间", MAX_WORKER_ID));
        }
        if (dataCenterId > MAX_DATA_CENTER_ID || dataCenterId < 0) {
            throw new IllegalArgumentException(
                    String.format("数据中心ID必须在0-%d之间", MAX_DATA_CENTER_ID));
        }
        this.workerId = workerId;
        this.dataCenterId = dataCenterId;
    }

    /**
     * 生成下一个ID（线程安全）
     *
     * @return 雪花算法ID
     */
    public synchronized long generateId() {
        long timestamp = currentTimeMillis();

        // 时钟回拨检测
        if (timestamp < lastTimestamp) {
            long offset = lastTimestamp - timestamp;
            if (offset <= 5) {
                // 允许5ms内的时钟回拨，等待时钟追赶
                try {
                    Thread.sleep(offset * 2);
                    timestamp = currentTimeMillis();
                    if (timestamp < lastTimestamp) {
                        throw new RuntimeException(
                                String.format("时钟回拨异常，拒绝生成ID。当前时间：%d，上次时间：%d",
                                        timestamp, lastTimestamp));
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new RuntimeException("ID生成被中断", e);
                }
            } else {
                throw new RuntimeException(
                        String.format("时钟回拨异常，回拨超过5ms。当前时间：%d，上次时间：%d",
                                timestamp, lastTimestamp));
            }
        }

        // 同一毫秒内序列号递增
        if (lastTimestamp == timestamp) {
            sequence = (sequence + 1) & SEQUENCE_MASK;
            if (sequence == 0) {
                // 序列号溢出，等待下一毫秒
                timestamp = waitNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0L;
        }

        lastTimestamp = timestamp;

        return ((timestamp - EPOCH) << TIMESTAMP_LEFT_SHIFT)
                | (dataCenterId << DATA_CENTER_ID_SHIFT)
                | (workerId << WORKER_ID_SHIFT)
                | sequence;
    }

    private long waitNextMillis(long lastTimestamp) {
        long timestamp = currentTimeMillis();
        while (timestamp <= lastTimestamp) {
            timestamp = currentTimeMillis();
        }
        return timestamp;
    }

    private long currentTimeMillis() {
        return System.currentTimeMillis();
    }

    // ==================== 静态方法（使用默认实例）====================

    /**
     * 生成下一个Long型ID
     */
    public static long nextId() {
        return DEFAULT_INSTANCE.generateId();
    }

    /**
     * 生成下一个字符串型ID
     */
    public static String nextStrId() {
        return String.valueOf(nextId());
    }
}
