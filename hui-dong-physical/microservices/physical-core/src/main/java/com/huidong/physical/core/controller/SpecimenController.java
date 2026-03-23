package com.huidong.physical.core.controller;

import com.huidong.physical.common.result.R;
import com.huidong.physical.core.entity.Specimen;
import com.huidong.physical.core.service.SpecimenService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

/**
 * 标本管理接口
 * 支持院内扫码关联居民体检单
 */
@Api(tags = "标本管理")
@RestController
@RequestMapping("/specimen")
@RequiredArgsConstructor
public class SpecimenController {

    private final SpecimenService specimenService;

    @ApiOperation("院内扫码：标本关联体检单")
    @PostMapping("/bind")
    public R<Specimen> bind(@RequestBody BindRequest req) {
        return R.ok(specimenService.bindSpecimenToExam(req.getBarcodeNo(), req.getExamRecordId()));
    }

    @ApiOperation("按条码号查询标本")
    @GetMapping("/by-barcode/{barcodeNo}")
    public R<Specimen> getByBarcode(@PathVariable String barcodeNo) {
        return R.ok(specimenService.getByBarcodeNo(barcodeNo));
    }

    @Data
    static class BindRequest {
        @NotBlank(message = "条码号不能为空")
        private String barcodeNo;
        @NotNull(message = "体检单ID不能为空")
        private Long examRecordId;
    }
}
