package com.hd.dr.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.dr.entity.DrOrder;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface DrOrderMapper extends BaseMapper<DrOrder> {

    IPage<DrOrder> selectOrderPage(Page<DrOrder> page,
                                   @Param("residentName") String residentName,
                                   @Param("idCard") String idCard,
                                   @Param("status") Integer status,
                                   @Param("applyDeptId") Long applyDeptId);
}
