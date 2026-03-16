package com.ilbuy.report.repository;

import com.ilbuy.report.model.entity.Report;
import com.ilbuy.report.model.enums.ReportStatus;
import com.ilbuy.report.model.enums.ReportType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ReportRepository extends JpaRepository<Report, Long> {

    Optional<Report> findByReportNoAndDeletedFalse(String reportNo);

    Page<Report> findByUserIdAndDeletedFalse(Long userId, Pageable pageable);

    Page<Report> findByUserIdAndTypeAndDeletedFalse(Long userId, ReportType type, Pageable pageable);

    Page<Report> findByUserIdAndStatusAndDeletedFalse(Long userId, ReportStatus status, Pageable pageable);

    Page<Report> findByUserIdAndTypeAndStatusAndDeletedFalse(Long userId, ReportType type, ReportStatus status, Pageable pageable);
}
