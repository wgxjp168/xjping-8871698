package com.health.physical.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.physical.auth.entity.Doctor;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 医生账号Mapper
 */
@Mapper
public interface DoctorMapper extends BaseMapper<Doctor> {

    /**
     * 按用户名查询（不含已删除）
     */
    Doctor selectByUsername(@Param("username") String username);

    /**
     * 按县域医生ID查询
     */
    Doctor selectByDocId(@Param("docId") String docId);
}
