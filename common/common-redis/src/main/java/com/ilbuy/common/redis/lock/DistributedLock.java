package com.ilbuy.common.redis.lock;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * 基于 Redisson 的分布式锁工具类
 *
 * <p>提供多种加锁方式：
 * <ul>
 *   <li>tryLock - 尝试获取锁（非阻塞，推荐）</li>
 *   <li>lock - 阻塞式获取锁</li>
 *   <li>lockWithAction - 带回调的加锁（自动释放）</li>
 * </ul>
 *
 * <p>使用场景：
 * <ul>
 *   <li>采购决策幂等性保证（防止重复提交）</li>
 *   <li>订单创建防重（同一用户同时发起多次）</li>
 *   <li>会员配额扣减（防超卖）</li>
 * </ul>
 *
 * <p>使用示例：
 * <pre>{@code
 * // 方式1：带回调（推荐，自动释放）
 * String result = distributedLock.lockWithResult(
 *     "decision:lock:" + userId,
 *     30, TimeUnit.SECONDS,
 *     () -> aiDecisionService.process(request)
 * );
 *
 * // 方式2：手动管理
 * boolean locked = distributedLock.tryLock("order:lock:" + orderId, 10, 30, TimeUnit.SECONDS);
 * try {
 *     // 业务逻辑
 * } finally {
 *     distributedLock.unlock("order:lock:" + orderId);
 * }
 * }</pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DistributedLock {

    private final RedissonClient redissonClient;

    /** 默认锁等待时间（秒）*/
    private static final long DEFAULT_WAIT_TIME = 3L;
    /** 默认锁持有时间（秒）*/
    private static final long DEFAULT_LEASE_TIME = 30L;

    /**
     * 尝试获取锁（非阻塞）
     *
     * @param lockKey   锁键（建议带业务前缀，如 "decision:lock:userId"）
     * @param waitTime  等待时间（超时则返回false）
     * @param leaseTime 锁持有时间（超时自动释放，防止死锁）
     * @param unit      时间单位
     * @return true-获取成功，false-获取失败
     */
    public boolean tryLock(String lockKey, long waitTime, long leaseTime, TimeUnit unit) {
        try {
            RLock lock = redissonClient.getLock(lockKey);
            boolean acquired = lock.tryLock(waitTime, leaseTime, unit);
            if (!acquired) {
                log.debug("[DistributedLock] 获取锁失败，锁已被占用: key={}", lockKey);
            }
            return acquired;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("[DistributedLock] 获取锁被中断: key={}", lockKey);
            return false;
        }
    }

    /**
     * 快速尝试获取锁（使用默认超时）
     */
    public boolean tryLock(String lockKey) {
        return tryLock(lockKey, DEFAULT_WAIT_TIME, DEFAULT_LEASE_TIME, TimeUnit.SECONDS);
    }

    /**
     * 释放锁（仅当当前线程持有该锁时才释放）
     *
     * @param lockKey 锁键
     */
    public void unlock(String lockKey) {
        try {
            RLock lock = redissonClient.getLock(lockKey);
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
                log.debug("[DistributedLock] 锁已释放: key={}", lockKey);
            }
        } catch (Exception e) {
            log.warn("[DistributedLock] 释放锁异常: key={}, error={}", lockKey, e.getMessage());
        }
    }

    /**
     * 带回调的加锁执行（自动加锁/释放，无返回值）
     *
     * @param lockKey   锁键
     * @param leaseTime 锁持有时间（秒）
     * @param action    锁内执行的业务逻辑
     * @return true-执行成功，false-获取锁失败
     */
    public boolean lockWithAction(String lockKey, long leaseTime, Runnable action) {
        boolean locked = tryLock(lockKey, DEFAULT_WAIT_TIME, leaseTime, TimeUnit.SECONDS);
        if (!locked) {
            return false;
        }
        try {
            action.run();
            return true;
        } finally {
            unlock(lockKey);
        }
    }

    /**
     * 带回调的加锁执行（自动加锁/释放，有返回值）
     *
     * @param lockKey   锁键
     * @param leaseTime 锁持有时间（秒）
     * @param supplier  锁内执行的业务逻辑（有返回值）
     * @param <T>       返回值类型
     * @return 业务逻辑返回值，获取锁失败则返回null
     */
    public <T> T lockWithResult(String lockKey, long leaseTime, Supplier<T> supplier) {
        boolean locked = tryLock(lockKey, DEFAULT_WAIT_TIME, leaseTime, TimeUnit.SECONDS);
        if (!locked) {
            log.warn("[DistributedLock] 无法获取锁，操作已跳过: key={}", lockKey);
            return null;
        }
        try {
            return supplier.get();
        } finally {
            unlock(lockKey);
        }
    }

    /**
     * 判断锁是否被占用
     *
     * @param lockKey 锁键
     * @return true-锁被占用中
     */
    public boolean isLocked(String lockKey) {
        return redissonClient.getLock(lockKey).isLocked();
    }
}
