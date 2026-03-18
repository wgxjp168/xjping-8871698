package com.ilbuy.common.mybatis.injector;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.mybatis.entity.BaseEntity;

import java.io.Serializable;
import java.util.Optional;

/**
 * ILbuy 服务基类（扩展 ServiceImpl，提供常用便捷方法）
 *
 * <pre>{@code
 * @Service
 * public class UserServiceImpl extends ILbuyServiceImpl<UserMapper, UserDO>
 *         implements UserService {
 *
 *     public UserDO getOrThrow(Long id) {
 *         return getByIdOrThrow(id); // 自动抛 BizException
 *     }
 * }
 * }</pre>
 *
 * @param <M> Mapper 类型
 * @param <T> 实体类型（需继承 BaseEntity）
 */
public abstract class ILbuyServiceImpl<M extends ILbuyBaseMapper<T>, T extends BaseEntity>
        extends ServiceImpl<M, T> {

    /**
     * 根据 ID 查询，不存在则抛 {@link BizException}
     */
    public T getByIdOrThrow(Serializable id) {
        T entity = getById(id);
        if (entity == null) {
            throw new BizException(ResultCode.DATA_NOT_EXIST);
        }
        return entity;
    }

    /**
     * 根据 ID 查询，返回 Optional
     */
    public Optional<T> findById(Serializable id) {
        return Optional.ofNullable(getById(id));
    }

    /**
     * 检查是否存在（通过主键）
     */
    public boolean existsById(Serializable id) {
        return getById(id) != null;
    }

    /**
     * 构建 LambdaQueryWrapper（快捷方法）
     */
    protected LambdaQueryWrapper<T> lambdaQuery() {
        return Wrappers.lambdaQuery(currentModelClass());
    }
}
