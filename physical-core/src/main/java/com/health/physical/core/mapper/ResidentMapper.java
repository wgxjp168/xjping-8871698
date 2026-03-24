package com.health.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.physical.common.entity.Resident;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 居民Mapper
 */
@Mapper
public interface ResidentMapper extends BaseMapper<Resident> {

    Resident selectByIdCard(@Param("idCard") String idCard);

    Resident selectByCountyId(@Param("countyResidentId") String countyResidentId);
}
