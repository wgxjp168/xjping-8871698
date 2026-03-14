package com.ilbuy.common.core.utils;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 雪花算法ID生成器单元测试
 *
 * @author ILbuy Team
 */
@DisplayName("雪花算法ID生成器测试")
class IdGeneratorTest {

    @Test
    @DisplayName("生成的ID为正数")
    void testIdIsPositive() {
        long id = IdGenerator.nextId();
        assertThat(id).isPositive();
    }

    @Test
    @DisplayName("连续生成的ID单调递增")
    void testIdsAreMonotonicallyIncreasing() {
        long id1 = IdGenerator.nextId();
        long id2 = IdGenerator.nextId();
        long id3 = IdGenerator.nextId();
        assertThat(id1).isLessThan(id2);
        assertThat(id2).isLessThan(id3);
    }

    @Test
    @DisplayName("并发环境下1000个ID全部唯一")
    void testIdsAreUniqueUnderConcurrency() throws InterruptedException {
        int threadCount = 10;
        int idsPerThread = 100;
        Set<Long> ids = ConcurrentHashMap.newKeySet();
        CountDownLatch latch = new CountDownLatch(threadCount);

        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                for (int j = 0; j < idsPerThread; j++) {
                    ids.add(IdGenerator.nextId());
                }
                latch.countDown();
            });
        }
        latch.await();
        executor.shutdown();

        // 1000个ID应全部唯一
        assertThat(ids).hasSize(threadCount * idsPerThread);
    }

    @Test
    @DisplayName("字符串ID格式正确")
    void testStrId() {
        String strId = IdGenerator.nextStrId();
        assertThat(strId).isNotBlank();
        assertThat(Long.parseLong(strId)).isPositive();
    }
}
