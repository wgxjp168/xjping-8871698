package com.ilbuy.common.mybatis;

import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.BlockAttackInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.OptimisticLockerInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import com.ilbuy.common.mybatis.config.MybatisPlusConfig;
import com.ilbuy.common.mybatis.handler.MetaObjectFillHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("MybatisPlusConfig 单元测试")
class MybatisPlusConfigTest {

    private MybatisPlusConfig config;

    @BeforeEach
    void setUp() {
        config = new MybatisPlusConfig();
    }

    @Test
    @DisplayName("插件链包含分页/乐观锁/防攻击插件")
    void interceptor_containsAllPlugins() {
        MybatisPlusInterceptor interceptor = config.mybatisPlusInterceptor();

        boolean hasPagination    = interceptor.getInterceptors().stream()
                .anyMatch(i -> i instanceof PaginationInnerInterceptor);
        boolean hasOptimisticLock = interceptor.getInterceptors().stream()
                .anyMatch(i -> i instanceof OptimisticLockerInnerInterceptor);
        boolean hasBlockAttack   = interceptor.getInterceptors().stream()
                .anyMatch(i -> i instanceof BlockAttackInnerInterceptor);

        assertThat(hasPagination).isTrue();
        assertThat(hasOptimisticLock).isTrue();
        assertThat(hasBlockAttack).isTrue();
    }

    @Test
    @DisplayName("插件顺序：分页在乐观锁之前")
    void interceptor_orderCorrect() {
        MybatisPlusInterceptor interceptor = config.mybatisPlusInterceptor();
        var interceptors = interceptor.getInterceptors();

        int paginationIdx   = -1;
        int optimisticIdx   = -1;

        for (int i = 0; i < interceptors.size(); i++) {
            if (interceptors.get(i) instanceof PaginationInnerInterceptor)    paginationIdx  = i;
            if (interceptors.get(i) instanceof OptimisticLockerInnerInterceptor) optimisticIdx = i;
        }

        assertThat(paginationIdx).isLessThan(optimisticIdx);
    }

    @Test
    @DisplayName("GlobalConfig 引用填充处理器")
    void globalConfig_hasFillHandler() {
        MetaObjectFillHandler handler = Mockito.mock(MetaObjectFillHandler.class);
        var gc = config.globalConfig(handler);
        assertThat(gc.getMetaObjectHandler()).isSameAs(handler);
    }

    @Test
    @DisplayName("MetaObjectFillHandler Bean 正常实例化")
    void fillHandler_instantiates() {
        MetaObjectFillHandler handler = new MetaObjectFillHandler();
        assertThat(handler).isNotNull();
    }
}
