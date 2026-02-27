package com.ilbuy.business.service;

import com.ilbuy.business.exception.ResourceNotFoundException;
import com.ilbuy.business.model.User;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class UserService {

    private static final Logger log = LoggerFactory.getLogger(UserService.class);
    private final Map<String, User> users = new ConcurrentHashMap<>();

    public UserService() {
        User u1 = new User("U001", "zhangsan", "zhangsan@ilbuy.com", "13800138001", "张三");
        u1.setMemberLevel("VIP");
        User u2 = new User("U002", "lisi", "lisi@ilbuy.com", "13800138002", "李四");
        User u3 = new User("U003", "wangwu", "wangwu@ilbuy.com", "13800138003", "王五");
        u3.setMemberLevel("SVIP");
        users.put(u1.getId(), u1);
        users.put(u2.getId(), u2);
        users.put(u3.getId(), u3);
    }

    public List<User> findAll() {
        return new ArrayList<>(users.values());
    }

    public User findById(String id) {
        User user = users.get(id);
        if (user == null) throw new ResourceNotFoundException("用户不存在: " + id);
        return user;
    }

    public User create(User user) {
        String id = "U" + String.format("%03d", users.size() + 1);
        user.setId(id);
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());
        if (user.getMemberLevel() == null) user.setMemberLevel("NORMAL");
        users.put(id, user);
        log.info("创建用户: id={}, username={}", id, user.getUsername());
        return user;
    }

    public User update(String id, User updated) {
        User user = findById(id);
        if (updated.getNickname() != null) user.setNickname(updated.getNickname());
        if (updated.getEmail() != null) user.setEmail(updated.getEmail());
        if (updated.getPhone() != null) user.setPhone(updated.getPhone());
        if (updated.getAvatar() != null) user.setAvatar(updated.getAvatar());
        user.setUpdatedAt(LocalDateTime.now());
        log.info("更新用户: id={}", id);
        return user;
    }

    public void delete(String id) {
        if (users.remove(id) == null) throw new ResourceNotFoundException("用户不存在: " + id);
        log.info("删除用户: id={}", id);
    }
}
