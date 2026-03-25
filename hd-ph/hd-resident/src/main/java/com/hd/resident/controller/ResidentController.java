package com.hd.resident.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.hd.common.result.Result;
import com.hd.resident.entity.Resident;
import com.hd.resident.service.ResidentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/residents")
public class ResidentController {

    @Autowired
    private ResidentService residentService;

    @GetMapping
    public Result<IPage<Resident>> page(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String idCard,
            @RequestParam(required = false) String town,
            @RequestParam(required = false) Long deptId) {
        return Result.success(residentService.page(current, size, name, idCard, town, deptId));
    }

    @GetMapping("/{id}")
    public Result<Resident> getById(@PathVariable Long id) {
        return Result.success(residentService.getById(id));
    }

    @GetMapping("/by-idcard/{idCard}")
    public Result<Resident> getByIdCard(@PathVariable String idCard) {
        return Result.success(residentService.getByIdCard(idCard));
    }

    @PostMapping
    public Result<Void> create(@RequestBody Resident resident) {
        residentService.create(resident);
        return Result.success(null);
    }

    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody Resident resident) {
        resident.setId(id);
        residentService.update(resident);
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        residentService.delete(id);
        return Result.success(null);
    }

    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("hd-resident OK");
    }
}
