package com.huidong.physical.core.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.huidong.physical.core.dto.CreateExamRecordDTO;
import com.huidong.physical.core.dto.ExamRecordVO;
import com.huidong.physical.core.entity.ExamRecord;

/**
 * 体检记录服务接口
 */
public interface ExamRecordService extends IService<ExamRecord> {

    /**
     * 创建体检单
     */
    ExamRecord createExamRecord(CreateExamRecordDTO dto);

    /**
     * 按体检单号查询体检详情（含检验结果）
     */
    ExamRecordVO getExamDetail(String examNo);

    /**
     * 接收检验结果并更新体检单状态
     */
    void receiveLabResult(Long examRecordId, String labType);

    /**
     * 完成体检单
     */
    void completeExam(String examNo);
}
