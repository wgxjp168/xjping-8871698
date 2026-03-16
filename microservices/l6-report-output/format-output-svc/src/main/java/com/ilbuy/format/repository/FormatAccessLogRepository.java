package com.ilbuy.format.repository;

import com.ilbuy.format.model.entity.FormatAccessLog;
import com.ilbuy.format.model.enums.FormatType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface FormatAccessLogRepository extends JpaRepository<FormatAccessLog, Long> {

    List<FormatAccessLog> findByFormatJobFormatJobNo(String formatJobNo);

    @Query("SELECT COUNT(l) FROM FormatAccessLog l WHERE l.formatJob.id = :jobId AND l.format = :format")
    long countByJobIdAndFormat(@Param("jobId") Long jobId, @Param("format") FormatType format);

    @Query("SELECT l FROM FormatAccessLog l WHERE l.userId = :userId ORDER BY l.accessedAt DESC")
    List<FormatAccessLog> findByUserId(@Param("userId") Long userId);
}
