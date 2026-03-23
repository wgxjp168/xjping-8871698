package com.huidong.physical.core.dto;

import com.huidong.physical.core.entity.ExamRecord;
import com.huidong.physical.core.entity.LabResult;
import com.huidong.physical.core.entity.Specimen;
import lombok.Data;

import java.util.List;

/**
 * 体检详情视图对象
 */
@Data
public class ExamRecordVO {

    /** 体检主信息 */
    private ExamRecord examRecord;

    /** 居民姓名 */
    private String residentName;

    /** 居民身份证 */
    private String idCard;

    /** 标本列表 */
    private List<Specimen> specimens;

    /** 检验结果列表 */
    private List<LabResult> labResults;

    /** 同步状态描述 */
    private String syncStatusDesc;
}
