package com.ilbuy.data.service;

import com.ilbuy.data.entity.UserEntity;
import com.ilbuy.data.repository.UserRepository;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class DataUserService {

    private final UserRepository repo;

    public DataUserService(UserRepository repo) { this.repo = repo; }

    public List<UserEntity> findAll() { return repo.findAll(); }
    public UserEntity findById(String id) { return repo.findById(id).orElse(null); }
    public UserEntity save(UserEntity u) { return repo.save(u); }
    public void delete(String id) { repo.deleteById(id); }
    public List<UserEntity> findByMemberLevel(String level) { return repo.findByMemberLevel(level); }
}
