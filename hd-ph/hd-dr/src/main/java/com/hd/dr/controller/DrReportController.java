package com.hd.dr.controller;

import com.hd.common.result.Result;
import com.hd.dr.entity.DrReport;
import com.hd.dr.service.DrReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/dr-reports")
public class DrReportController {

    @Autowired
    private DrReportService reportService;

    @GetMapping("/order/{orderId}")
    public Result<DrReport> getByOrderId(@PathVariable Long orderId) {
        return Result.success(reportService.getByOrderId(orderId));
    }

    @PostMapping
    public Result<Void> submit(@RequestBody DrReport report,
                                @RequestHeader(value = "X-User-Id", required = false) Long userId) {
        report.setReportDoctorId(userId);
        reportService.submitReport(report);
        return Result.success(null);
    }

    @PutMapping("/{id}/upload")
    public Result<Void> markUploaded(@PathVariable Long id) {
        reportService.markUploaded(id);
        return Result.success(null);
    }
}
