package com.ilbuy.format.repository;

import com.ilbuy.format.model.entity.FormatJob;
import com.ilbuy.format.model.enums.FormatJobStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface FormatJobRepository extends JpaRepository<FormatJob, Long> {

    Optional<FormatJob> findByFormatJobNo(String formatJobNo);

    Optional<FormatJob> findByGeneratorJobNo(String generatorJobNo);

    List<FormatJob> findByUserId(Long userId);

    List<FormatJob> findByStatus(FormatJobStatus status);
}
