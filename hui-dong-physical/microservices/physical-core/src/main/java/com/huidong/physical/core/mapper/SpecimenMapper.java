package com.huidong.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huidong.physical.core.entity.Specimen;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 标本 Mapper
 */
@Mapper
public interface SpecimenMapper extends BaseMapper<Specimen> {

    /**
     * 按条码号查询标本
     */
    Specimen selectByBarcodeNo(@Param("barcodeNo") String barcodeNo);

    /**
     * 按体检单ID查询标本
     */
    java.util.List<Specimen> selectByExamRecordId(@Param("examRecordId") Long examRecordId);
}
