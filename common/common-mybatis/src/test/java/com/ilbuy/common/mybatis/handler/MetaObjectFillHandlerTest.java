package com.ilbuy.common.mybatis.handler;

import com.ilbuy.common.mybatis.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;
import org.apache.ibatis.reflection.MetaObject;
import org.apache.ibatis.reflection.SystemMetaObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("MetaObjectFillHandler 自动填充测试")
class MetaObjectFillHandlerTest {

    private MetaObjectFillHandler handler;

    @BeforeEach
    void setUp() {
        handler = new MetaObjectFillHandler();
    }

    @Test
    @DisplayName("INSERT 时 createTime 自动填充")
    void insertFill_createTime() {
        TestEntity entity    = new TestEntity();
        MetaObject metaObject = SystemMetaObject.forObject(entity);

        handler.insertFill(metaObject);

        assertThat(entity.getCreateTime()).isNotNull();
        assertThat(entity.getCreateTime()).isBeforeOrEqualTo(LocalDateTime.now());
    }

    @Test
    @DisplayName("INSERT 时 updateTime 自动填充")
    void insertFill_updateTime() {
        TestEntity entity    = new TestEntity();
        MetaObject metaObject = SystemMetaObject.forObject(entity);

        handler.insertFill(metaObject);

        assertThat(entity.getUpdateTime()).isNotNull();
    }

    @Test
    @DisplayName("INSERT 时 deleted 置 0")
    void insertFill_deletedIsZero() {
        TestEntity entity    = new TestEntity();
        MetaObject metaObject = SystemMetaObject.forObject(entity);

        handler.insertFill(metaObject);

        assertThat(entity.getDeleted()).isEqualTo(0);
    }

    @Test
    @DisplayName("INSERT 时 version 置 0")
    void insertFill_versionIsZero() {
        TestEntity entity    = new TestEntity();
        MetaObject metaObject = SystemMetaObject.forObject(entity);

        handler.insertFill(metaObject);

        assertThat(entity.getVersion()).isEqualTo(0);
    }

    @Test
    @DisplayName("UPDATE 时 updateTime 强制覆盖（即使已有值）")
    void updateFill_forceOverride() throws InterruptedException {
        TestEntity entity    = new TestEntity();
        LocalDateTime oldTime = LocalDateTime.of(2020, 1, 1, 0, 0, 0);
        entity.setUpdateTime(oldTime);

        MetaObject metaObject = SystemMetaObject.forObject(entity);
        Thread.sleep(10); // 确保时间差
        handler.updateFill(metaObject);

        assertThat(entity.getUpdateTime()).isAfter(oldTime);
    }

    @Test
    @DisplayName("INSERT 时已有 createTime 不被覆盖")
    void insertFill_existingValueNotOverridden() {
        TestEntity entity    = new TestEntity();
        LocalDateTime preset = LocalDateTime.of(2024, 6, 1, 0, 0, 0);
        entity.setCreateTime(preset);

        MetaObject metaObject = SystemMetaObject.forObject(entity);
        handler.insertFill(metaObject);

        assertThat(entity.getCreateTime()).isEqualTo(preset);
    }

    // ───────── 测试用实体 ─────────

    @Data
    @EqualsAndHashCode(callSuper = true)
    static class TestEntity extends BaseEntity {
        private String name;
    }
}
