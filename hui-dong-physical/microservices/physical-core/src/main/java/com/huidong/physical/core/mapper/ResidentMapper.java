package com.huidong.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huidong.physical.core.entity.Resident;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 居民信息 Mapper
 */
@Mapper
public interface ResidentMapper extends BaseMapper<Resident> {

    /**
     * 按身份证号查询居民
     */
    Resident selectByIdCard(@Param("idCard") String idCard);

    /**
     * 按居民编码查询
     */
    Resident selectByResidentCode(@Param("residentCode") String residentCode);
}
