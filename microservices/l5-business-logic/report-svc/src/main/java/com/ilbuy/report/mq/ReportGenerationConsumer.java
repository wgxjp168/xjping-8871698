package com.ilbuy.report.mq;

import com.ilbuy.report.model.entity.Report;
import com.ilbuy.report.model.enums.ReportStatus;
import com.ilbuy.report.repository.ReportRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Random;

@Component
@RequiredArgsConstructor
@Slf4j
public class ReportGenerationConsumer {

    private final ReportRepository reportRepository;
    private final Random random = new Random();

    @RabbitListener(queues = "${rabbitmq.report.queue}")
    @Transactional
    public void handleReportGenerate(Map<String, Object> event) {
        String reportNo = (String) event.get("reportNo");
        log.info("Received report.generate event for reportNo={}", reportNo);

        Report report = reportRepository.findByReportNoAndDeletedFalse(reportNo)
            .orElse(null);

        if (report == null) {
            log.warn("Report not found for reportNo={}, skipping", reportNo);
            return;
        }

        if (report.getStatus() != ReportStatus.PENDING) {
            log.warn("Report {} is in status {}, expected PENDING – skipping", reportNo, report.getStatus());
            return;
        }

        // Transition: PENDING -> GENERATING
        report.setStatus(ReportStatus.GENERATING);
        reportRepository.save(report);
        log.info("Report {} status set to GENERATING", reportNo);

        try {
            // Simulate generation (2 seconds)
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Report generation interrupted for reportNo={}", reportNo);
            report.setStatus(ReportStatus.FAILED);
            reportRepository.save(report);
            return;
        }

        // Transition: GENERATING -> READY
        report.setStatus(ReportStatus.READY);
        report.setFileUrl("https://storage.ilbuy.com/reports/" + reportNo + ".pdf");
        report.setFileSize(1024L * (100 + random.nextInt(900))); // 100KB ~ 1000KB simulated
        report.setExpiresAt(LocalDateTime.now().plusDays(30));
        reportRepository.save(report);

        log.info("Report {} generation complete – status=READY, fileUrl={}", reportNo, report.getFileUrl());
    }
}
