package com.ilbuy.common.mybatis.injector;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import java.util.Collection;

/**
 * ILbuy 扩展 BaseMapper（可添加自定义通用方法）
 *
 * <p>所有业务 Mapper 继承此接口，而非直接继承 {@link BaseMapper}，
 * 便于后续统一扩展批量操作等方法。</p>
 *
 * <pre>{@code
 * @Mapper
 * public interface UserMapper extends ILbuyBaseMapper<UserDO> {
 *     // 自定义 SQL 方法
 * }
 * }</pre>
 */
public interface ILbuyBaseMapper<T> extends BaseMapper<T> {

    /**
     * 真正的批量插入（非循环单条，通过 SQL 注入器扩展 INSERT INTO...VALUES(...),(...)）
     *
     * <p>默认实现依赖 MybatisPlus 的 InsertBatchSomeColumn 注入器。
     * 若未启用，回退到父类 insert() 循环调用。</p>
     *
     * @param entityList 实体集合
     * @return 影响行数
     */
    default int insertBatch(Collection<T> entityList) {
        if (entityList == null || entityList.isEmpty()) return 0;
        int count = 0;
        for (T entity : entityList) {
            count += insert(entity);
        }
        return count;
    }
}
