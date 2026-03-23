package com.huidong.physical.core.controller;

import com.huidong.physical.common.result.R;
import com.huidong.physical.core.dto.CreateExamRecordDTO;
import com.huidong.physical.core.dto.ExamRecordVO;
import com.huidong.physical.core.entity.ExamRecord;
import com.huidong.physical.core.service.ExamRecordService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 体检记录接口
 */
@Api(tags = "体检记录管理")
@RestController
@RequestMapping("/exam")
@RequiredArgsConstructor
public class ExamRecordController {

    private final ExamRecordService examRecordService;

    @ApiOperation("创建体检单")
    @PostMapping
    public R<ExamRecord> create(@Validated @RequestBody CreateExamRecordDTO dto) {
        return R.ok(examRecordService.createExamRecord(dto));
    }

    @ApiOperation("查询体检详情（含检验结果）")
    @GetMapping("/{examNo}")
    public R<ExamRecordVO> detail(@PathVariable String examNo) {
        return R.ok(examRecordService.getExamDetail(examNo));
    }

    @ApiOperation("完成体检单")
    @PostMapping("/{examNo}/complete")
    public R<Void> complete(@PathVariable String examNo) {
        examRecordService.completeExam(examNo);
        return R.ok();
    }
}
