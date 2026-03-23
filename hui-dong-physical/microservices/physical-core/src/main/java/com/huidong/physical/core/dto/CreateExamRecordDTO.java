package com.huidong.physical.core.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.time.LocalDate;

/**
 * 创建体检单请求
 */
@Data
public class CreateExamRecordDTO {

    /** 居民编码或身份证号 */
    @NotBlank(message = "居民标识不能为空")
    private String residentIdentifier;

    /** 标识类型 1=居民编码 2=身份证号 */
    @NotNull(message = "标识类型不能为空")
    private Integer identifierType;

    /** 体检类型 1=下乡 2=院内 */
    @NotNull(message = "体检类型不能为空")
    private Integer examType;

    /** 体检日期 */
    private LocalDate examDate;

    /** 体检地点 */
    private String examLocation;
}
