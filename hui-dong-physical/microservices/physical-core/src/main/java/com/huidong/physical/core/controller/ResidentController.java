package com.huidong.physical.core.controller;

import com.huidong.physical.common.result.R;
import com.huidong.physical.core.entity.Resident;
import com.huidong.physical.core.service.ResidentService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 居民信息接口
 */
@Api(tags = "居民信息管理")
@RestController
@RequestMapping("/resident")
@RequiredArgsConstructor
public class ResidentController {

    private final ResidentService residentService;

    @ApiOperation("按身份证号查询居民")
    @GetMapping("/by-idcard/{idCard}")
    public R<Resident> getByIdCard(@PathVariable String idCard) {
        return R.ok(residentService.getByIdCard(idCard));
    }

    @ApiOperation("按居民编码查询居民")
    @GetMapping("/by-code/{residentCode}")
    public R<Resident> getByCode(@PathVariable String residentCode) {
        return R.ok(residentService.getByResidentCode(residentCode));
    }

    @ApiOperation("保存/更新居民信息")
    @PostMapping
    public R<Void> save(@RequestBody Resident resident) {
        residentService.saveOrUpdate(resident);
        return R.ok();
    }
}
