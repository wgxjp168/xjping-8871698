package com.hd.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.auth.entity.SysDoctorFilter;
import com.hd.auth.mapper.SysDoctorFilterMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DoctorFilterService {

    @Autowired
    private SysDoctorFilterMapper filterMapper;

    public List<SysDoctorFilter> listAll() {
        return filterMapper.selectList(
                new LambdaQueryWrapper<SysDoctorFilter>().orderByAsc(SysDoctorFilter::getSort)
        );
    }

    public List<SysDoctorFilter> listEnabled() {
        return filterMapper.selectList(
                new LambdaQueryWrapper<SysDoctorFilter>()
                        .eq(SysDoctorFilter::getStatus, 1)
                        .orderByAsc(SysDoctorFilter::getSort)
        );
    }

    public SysDoctorFilter getById(Long id) {
        return filterMapper.selectById(id);
    }

    public void create(SysDoctorFilter filter) {
        if (filter.getStatus() == null) filter.setStatus(1);
        filterMapper.insert(filter);
    }

    public void update(SysDoctorFilter filter) {
        filterMapper.updateById(filter);
    }

    public void delete(Long id) {
        filterMapper.deleteById(id);
    }
}
