package com.hd.resident.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.resident.entity.Resident;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface ResidentMapper extends BaseMapper<Resident> {

    IPage<Resident> selectResidentPage(Page<Resident> page,
                                       @Param("name") String name,
                                       @Param("idCard") String idCard,
                                       @Param("town") String town,
                                       @Param("deptId") Long deptId);
}
