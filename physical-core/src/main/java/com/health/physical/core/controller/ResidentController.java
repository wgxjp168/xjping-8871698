package com.health.physical.core.controller;

import com.health.physical.common.dto.PageResult;
import com.health.physical.common.dto.Result;
import com.health.physical.common.entity.Resident;
import com.health.physical.core.service.ResidentService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 居民管理接口
 */
@Api(tags = "居民管理")
@RestController
@RequestMapping("/residents")
@RequiredArgsConstructor
public class ResidentController {

    private final ResidentService residentService;

    @ApiOperation("按身份证查询居民")
    @GetMapping("/idcard/{idCard}")
    public Result<Resident> getByIdCard(@PathVariable String idCard) {
        Resident resident = residentService.getByIdCard(idCard);
        if (resident == null) {
            return Result.fail(404, "居民不存在");
        }
        return Result.ok(resident);
    }

    @ApiOperation("分页查询居民")
    @GetMapping("/page")
    public Result<PageResult<Resident>> pageQuery(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String village,
            @RequestParam(required = false) String town) {
        return Result.ok(PageResult.of(residentService.pageQuery(current, size, name, village, town)));
    }

    @ApiOperation("新增居民")
    @PostMapping
    public Result<Resident> save(@RequestBody Resident resident) {
        return Result.ok("新增成功", residentService.save(resident));
    }

    @ApiOperation("更新居民信息")
    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody Resident resident) {
        residentService.update(id, resident);
        return Result.ok("更新成功");
    }
}
