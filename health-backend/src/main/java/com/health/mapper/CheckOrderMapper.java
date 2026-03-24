package com.health.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.dto.CheckOrderQueryDTO;
import com.health.entity.CheckOrder;
import com.health.vo.CheckOrderVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 体检单 Mapper
 */
@Mapper
public interface CheckOrderMapper extends BaseMapper<CheckOrder> {

    Page<CheckOrderVO> queryOrderPage(Page<CheckOrderVO> page, @Param("query") CheckOrderQueryDTO query);

    CheckOrderVO getOrderDetail(@Param("orderId") Long orderId);
}
