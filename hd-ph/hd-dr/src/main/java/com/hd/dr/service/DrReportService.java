package com.hd.dr.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.dr.entity.DrOrder;
import com.hd.dr.entity.DrReport;
import com.hd.dr.mapper.DrOrderMapper;
import com.hd.dr.mapper.DrReportMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Service
public class DrReportService {

    @Autowired
    private DrReportMapper reportMapper;

    @Autowired
    private DrOrderMapper orderMapper;

    public DrReport getByOrderId(Long orderId) {
        return reportMapper.selectOne(
                new LambdaQueryWrapper<DrReport>()
                        .eq(DrReport::getDrOrderId, orderId)
                        .eq(DrReport::getDeleted, 0)
        );
    }

    @Transactional
    public void submitReport(DrReport report) {
        report.setReportTime(LocalDateTime.now());
        report.setUploadStatus(0);

        DrReport existing = getByOrderId(report.getDrOrderId());
        if (existing != null) {
            report.setId(existing.getId());
            reportMapper.updateById(report);
        } else {
            String reportNo = "RPT" + LocalDateTime.now().toString().replaceAll("[^0-9]", "").substring(0, 14);
            report.setReportNo(reportNo);
            reportMapper.insert(report);
        }

        // 更新申请单状态为已完成
        DrOrder order = new DrOrder();
        order.setId(report.getDrOrderId());
        order.setStatus(2);
        order.setFinishTime(LocalDateTime.now());
        orderMapper.updateById(order);
    }

    @Transactional
    public void markUploaded(Long id) {
        DrReport report = new DrReport();
        report.setId(id);
        report.setUploadStatus(1);
        report.setUploadTime(LocalDateTime.now());
        reportMapper.updateById(report);

        // 获取申请单并更新为已上传
        DrReport existing = reportMapper.selectById(id);
        if (existing != null) {
            DrOrder order = new DrOrder();
            order.setId(existing.getDrOrderId());
            order.setStatus(3);
            orderMapper.updateById(order);
        }
    }
}
