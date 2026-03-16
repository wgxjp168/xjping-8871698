package com.ilbuy.report.repository;

import com.ilbuy.report.model.entity.ReportAccessLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ReportAccessLogRepository extends JpaRepository<ReportAccessLog, Long> {

    List<ReportAccessLog> findByReportIdOrderByAccessedAtDesc(Long reportId);

    List<ReportAccessLog> findByUserIdOrderByAccessedAtDesc(Long userId);
}
