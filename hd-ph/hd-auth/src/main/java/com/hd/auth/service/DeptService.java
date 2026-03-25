package com.hd.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.auth.entity.SysDept;
import com.hd.auth.mapper.SysDeptMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DeptService {

    @Autowired
    private SysDeptMapper deptMapper;

    public List<SysDept> listAll() {
        return deptMapper.selectList(new LambdaQueryWrapper<SysDept>().eq(SysDept::getStatus, 1).orderByAsc(SysDept::getSort));
    }

    public SysDept getById(Long id) {
        return deptMapper.selectById(id);
    }

    public void create(SysDept dept) {
        deptMapper.insert(dept);
    }

    public void update(SysDept dept) {
        deptMapper.updateById(dept);
    }

    public void delete(Long id) {
        deptMapper.deleteById(id);
    }
}
