package com.ilbuy.reportgen.repository;

import com.ilbuy.reportgen.model.entity.ReportJob;
import com.ilbuy.reportgen.model.enums.JobStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface ReportJobRepository extends JpaRepository<ReportJob, Long> {

    Optional<ReportJob> findByJobNo(String jobNo);

    Optional<ReportJob> findByL5ReportNo(String l5ReportNo);

    List<ReportJob> findByUserId(Long userId);

    List<ReportJob> findByStatus(JobStatus status);

    @Modifying
    @Query("UPDATE ReportJob j SET j.status = :status, j.errorMessage = :error WHERE j.jobNo = :jobNo")
    int updateStatusAndError(@Param("jobNo") String jobNo,
                             @Param("status") JobStatus status,
                             @Param("error") String error);

    @Query("SELECT j FROM ReportJob j WHERE j.status = 'PENDING' OR (j.status = 'FAILED' AND j.retryCount < 3)")
    List<ReportJob> findPendingAndRetryableJobs();
}
