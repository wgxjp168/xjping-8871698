package com.health.physical.core.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.dto.PageResult;
import com.health.physical.common.dto.Result;
import com.health.physical.common.entity.Resident;
import com.health.physical.core.mapper.ResidentMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

/**
 * 居民管理接口
 */
@Api(tags = "居民管理")
@RestController
@RequestMapping("/residents")
@RequiredArgsConstructor
public class ResidentController {

    private final ResidentMapper residentMapper;

    @ApiOperation("按身份证查询居民")
    @GetMapping("/idcard/{idCard}")
    public Result<Resident> getByIdCard(@PathVariable String idCard) {
        Resident resident = residentMapper.selectByIdCard(idCard);
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
        Page<Resident> page = new Page<>(current, size);
        LambdaQueryWrapper<Resident> wrapper = new LambdaQueryWrapper<Resident>()
                .like(StringUtils.hasText(name), Resident::getName, name)
                .eq(StringUtils.hasText(village), Resident::getVillage, village)
                .eq(StringUtils.hasText(town), Resident::getTown, town)
                .orderByDesc(Resident::getCreateTime);
        residentMapper.selectPage(page, wrapper);
        return Result.ok(PageResult.of(page));
    }

    @ApiOperation("新增居民")
    @PostMapping
    public Result<Resident> save(@RequestBody Resident resident) {
        // 检查身份证是否已存在
        Resident existing = residentMapper.selectByIdCard(resident.getIdCard());
        if (existing != null) {
            return Result.fail("居民身份证已存在");
        }
        resident.setStatus(1);
        residentMapper.insert(resident);
        return Result.ok("新增成功", resident);
    }

    @ApiOperation("更新居民信息")
    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody Resident resident) {
        resident.setId(id);
        residentMapper.updateById(resident);
        return Result.ok("更新成功");
    }
}
