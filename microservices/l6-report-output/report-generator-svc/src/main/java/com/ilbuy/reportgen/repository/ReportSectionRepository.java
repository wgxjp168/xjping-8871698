package com.ilbuy.reportgen.repository;

import com.ilbuy.reportgen.model.entity.ReportSection;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReportSectionRepository extends JpaRepository<ReportSection, Long> {

    List<ReportSection> findByJobIdOrderByOrderIndexAsc(Long jobId);

    void deleteByJobId(Long jobId);
}
