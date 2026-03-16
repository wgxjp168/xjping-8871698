package com.ilbuy.user.repository;

import com.ilbuy.user.model.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    Optional<User> findByPhone(String phone);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);

    /** 支持用户名 / 邮箱 / 手机号 统一查询 */
    @Query("SELECT u FROM User u WHERE u.username = :p OR u.email = :p OR u.phone = :p")
    Optional<User> findByPrincipal(@Param("p") String principal);
}
