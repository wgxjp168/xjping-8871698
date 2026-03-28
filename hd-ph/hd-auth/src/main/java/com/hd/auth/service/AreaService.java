package com.hd.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.auth.entity.SysArea;
import com.hd.auth.mapper.SysAreaMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AreaService {

    @Autowired
    private SysAreaMapper areaMapper;

    public List<SysArea> listAll() {
        return areaMapper.selectList(
                new LambdaQueryWrapper<SysArea>()
                        .orderByAsc(SysArea::getAreaLevel)
                        .orderByAsc(SysArea::getSort)
        );
    }

    public SysArea getById(Long id) {
        return areaMapper.selectById(id);
    }

    public void create(SysArea area) {
        if (area.getStatus() == null) area.setStatus(1);
        areaMapper.insert(area);
    }

    public void update(SysArea area) {
        areaMapper.updateById(area);
    }

    public void delete(Long id) {
        areaMapper.deleteById(id);
    }
}
