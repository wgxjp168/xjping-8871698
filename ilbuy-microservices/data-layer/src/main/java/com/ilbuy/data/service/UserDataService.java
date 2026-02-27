package com.ilbuy.data.service;

import com.ilbuy.data.entity.UserEntity;
import com.ilbuy.data.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class UserDataService {

    private static final Logger log = LoggerFactory.getLogger(UserDataService.class);
    private final UserRepository userRepository;

    public UserDataService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Transactional(readOnly = true)
    public List<UserEntity> findAll() {
        return userRepository.findAll();
    }

    @Transactional(readOnly = true)
    public Optional<UserEntity> findById(String id) {
        return userRepository.findById(id);
    }

    @Transactional(readOnly = true)
    public Optional<UserEntity> findByUsername(String username) {
        return userRepository.findByUsername(username);
    }

    @Transactional(readOnly = true)
    public List<UserEntity> findByMemberLevel(String level) {
        return userRepository.findByMemberLevel(level);
    }

    public UserEntity save(UserEntity user) {
        UserEntity saved = userRepository.save(user);
        log.info("保存用户: id={}, username={}", saved.getId(), saved.getUsername());
        return saved;
    }

    public void deleteById(String id) {
        userRepository.deleteById(id);
        log.info("删除用户: id={}", id);
    }

    @Transactional(readOnly = true)
    public long count() {
        return userRepository.count();
    }
}
