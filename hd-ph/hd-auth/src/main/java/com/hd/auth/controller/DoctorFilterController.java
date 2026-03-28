package com.hd.auth.controller;

import com.hd.auth.entity.SysDoctorFilter;
import com.hd.auth.service.DoctorFilterService;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/doctor-filters")
public class DoctorFilterController {

    @Autowired
    private DoctorFilterService doctorFilterService;

    @GetMapping
    public Result<List<SysDoctorFilter>> list() {
        return Result.success(doctorFilterService.listAll());
    }

    @GetMapping("/enabled")
    public Result<List<SysDoctorFilter>> listEnabled() {
        return Result.success(doctorFilterService.listEnabled());
    }

    @GetMapping("/{id}")
    public Result<SysDoctorFilter> getById(@PathVariable Long id) {
        return Result.success(doctorFilterService.getById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody SysDoctorFilter filter) {
        doctorFilterService.create(filter);
        return Result.success(null);
    }

    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody SysDoctorFilter filter) {
        filter.setId(id);
        doctorFilterService.update(filter);
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        doctorFilterService.delete(id);
        return Result.success(null);
    }
}
