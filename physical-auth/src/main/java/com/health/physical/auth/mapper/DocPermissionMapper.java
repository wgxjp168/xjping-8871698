package com.health.physical.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.physical.auth.entity.DocPermission;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 医生权限Mapper
 */
@Mapper
public interface DocPermissionMapper extends BaseMapper<DocPermission> {

    /**
     * 查询医生有效权限列表
     */
    List<DocPermission> selectByDocId(@Param("docId") String docId);

    /**
     * 校验医生是否有指定项目的操作权限
     */
    int countPermission(@Param("docId") String docId,
                        @Param("projectCode") String projectCode,
                        @Param("operateType") String operateType);

    /**
     * 批量插入或更新权限
     */
    int batchInsertOrUpdate(@Param("list") List<DocPermission> list);
}
