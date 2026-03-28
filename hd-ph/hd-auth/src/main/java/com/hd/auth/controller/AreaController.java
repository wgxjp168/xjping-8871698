package com.hd.auth.controller;

import com.hd.auth.entity.SysArea;
import com.hd.auth.service.AreaService;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/areas")
public class AreaController {

    @Autowired
    private AreaService areaService;

    @GetMapping
    public Result<List<SysArea>> list() {
        return Result.success(areaService.listAll());
    }

    @GetMapping("/{id}")
    public Result<SysArea> getById(@PathVariable Long id) {
        return Result.success(areaService.getById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody SysArea area) {
        areaService.create(area);
        return Result.success(null);
    }

    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody SysArea area) {
        area.setId(id);
        areaService.update(area);
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        areaService.delete(id);
        return Result.success(null);
    }
}
