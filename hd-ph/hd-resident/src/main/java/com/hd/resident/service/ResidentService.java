package com.hd.resident.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.resident.entity.Resident;
import com.hd.resident.mapper.ResidentMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class ResidentService {

    @Autowired
    private ResidentMapper residentMapper;

    public IPage<Resident> page(int current, int size, String name, String idCard, String town, Long deptId) {
        Page<Resident> pageParam = new Page<>(current, size);
        return residentMapper.selectResidentPage(pageParam, name, idCard, town, deptId);
    }

    public Resident getById(Long id) {
        return residentMapper.selectById(id);
    }

    public Resident getByIdCard(String idCard) {
        return residentMapper.selectOne(
                new LambdaQueryWrapper<Resident>().eq(Resident::getIdCard, idCard).eq(Resident::getDeleted, 0)
        );
    }

    public void create(Resident resident) {
        // 检查身份证唯一性
        Resident existing = getByIdCard(resident.getIdCard());
        if (existing != null) {
            throw new RuntimeException("身份证号已存在: " + resident.getIdCard());
        }
        residentMapper.insert(resident);
    }

    public void update(Resident resident) {
        residentMapper.updateById(resident);
    }

    public long count() {
        return residentMapper.selectCount(
                new LambdaQueryWrapper<Resident>().eq(Resident::getDeleted, 0)
        );
    }

    public void delete(Long id) {
        Resident r = new Resident();
        r.setId(id);
        r.setDeleted(1);
        residentMapper.updateById(r);
    }
}
