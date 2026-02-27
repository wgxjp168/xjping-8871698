package com.ilbuy.data.repository;

import com.ilbuy.data.entity.UserEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<UserEntity, String> {

    Optional<UserEntity> findByUsername(String username);

    Optional<UserEntity> findByEmail(String email);

    List<UserEntity> findByMemberLevel(String memberLevel);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);
}
