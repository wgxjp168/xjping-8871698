package com.hd.check.controller;

import com.hd.check.entity.CheckResult;
import com.hd.check.service.CheckResultService;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/check-results")
public class CheckResultController {

    @Autowired
    private CheckResultService resultService;

    @GetMapping("/order/{orderId}")
    public Result<List<CheckResult>> listByOrder(@PathVariable Long orderId,
                                                  @RequestParam(required = false) String category) {
        if (category != null && !category.isEmpty()) {
            return Result.success(resultService.listByOrderAndCategory(orderId, category));
        }
        return Result.success(resultService.listByOrder(orderId));
    }

    @GetMapping("/resident/{residentId}")
    public Result<List<CheckResult>> listByResident(@PathVariable Long residentId) {
        return Result.success(resultService.listByResident(residentId));
    }

    @PostMapping
    public Result<Void> save(@RequestBody CheckResult result) {
        resultService.saveOrUpdate(result);
        return Result.success(null);
    }

    @PostMapping("/batch")
    public Result<Void> saveBatch(@RequestBody List<CheckResult> results) {
        resultService.saveResults(results);
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        resultService.delete(id);
        return Result.success(null);
    }
}
