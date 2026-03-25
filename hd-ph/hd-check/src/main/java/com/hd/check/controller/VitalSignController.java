package com.hd.check.controller;

import com.hd.check.entity.VitalSign;
import com.hd.check.service.VitalSignService;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/vital-signs")
public class VitalSignController {

    @Autowired
    private VitalSignService vitalSignService;

    @GetMapping("/order/{orderId}")
    public Result<VitalSign> getByOrder(@PathVariable Long orderId) {
        return Result.success(vitalSignService.getByOrder(orderId));
    }

    @PostMapping
    public Result<Void> save(@RequestBody VitalSign vital) {
        vitalSignService.saveOrUpdate(vital);
        return Result.success(null);
    }

    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("hd-check OK");
    }
}
