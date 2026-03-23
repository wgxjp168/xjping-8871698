package com.huidong.physical.urine.controller;

import com.huidong.physical.common.result.R;
import com.huidong.physical.urine.dto.UrineUploadDTO;
import com.huidong.physical.urine.dto.UrineUploadResultVO;
import com.huidong.physical.urine.service.UrineUploadService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 下乡尿机数据上传接口
 * 供手提电脑通过4G/5G调用
 */
@Api(tags = "下乡尿机数据上传")
@RestController
@RequestMapping("/urine")
@RequiredArgsConstructor
public class UrineUploadController {

    private final UrineUploadService urineUploadService;

    @ApiOperation("上传尿常规数据（下乡手提电脑专用）")
    @PostMapping("/upload")
    public R<UrineUploadResultVO> upload(@Validated @RequestBody UrineUploadDTO dto) {
        return R.ok(urineUploadService.upload(dto));
    }

    @ApiOperation("查询上传状态（断点续传检查）")
    @GetMapping("/status/{uploadId}")
    public R<String> queryStatus(@PathVariable String uploadId) {
        return R.ok(urineUploadService.queryUploadStatus(uploadId));
    }

    @ApiOperation("批量上传尿常规数据（弱网恢复场景）")
    @PostMapping("/upload/batch")
    public R<Void> batchUpload(@Validated @RequestBody java.util.List<UrineUploadDTO> list) {
        urineUploadService.batchUpload(list);
        return R.ok();
    }
}
