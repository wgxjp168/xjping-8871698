package com.ilbuy.common.mybatis.datasource;

import com.baomidou.dynamic.datasource.annotation.DS;

import java.lang.annotation.*;

/**
 * 只读数据源注解（路由到从库）
 *
 * <pre>{@code
 * @Service
 * public class UserServiceImpl implements UserService {
 *
 *     @ReadOnly
 *     public List<UserVO> list() { ... }
 *
 *     // 写操作使用默认主库，无需注解
 *     public void save(UserDTO dto) { ... }
 * }
 * }</pre>
 */
@Target({ElementType.TYPE, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
@DS(DataSourceType.SLAVE)
public @interface ReadOnly {
}
