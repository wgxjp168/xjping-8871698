package com.hd.check.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.check.entity.CheckOrder;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface CheckOrderMapper extends BaseMapper<CheckOrder> {

    IPage<CheckOrder> selectOrderPage(Page<CheckOrder> page,
                                      @Param("residentName") String residentName,
                                      @Param("idCard") String idCard,
                                      @Param("deptId") Long deptId,
                                      @Param("checkYear") Integer checkYear,
                                      @Param("status") Integer status);
}
