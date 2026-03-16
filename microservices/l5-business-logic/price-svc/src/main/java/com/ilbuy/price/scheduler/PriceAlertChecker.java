package com.ilbuy.price.scheduler;

import com.ilbuy.price.model.entity.PriceAlert;
import com.ilbuy.price.model.entity.PriceRecord;
import com.ilbuy.price.repository.PriceAlertRepository;
import com.ilbuy.price.repository.PriceRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Scheduled task that checks price alerts every 5 minutes.
 * For each untriggered alert, it fetches the latest price record and,
 * if the current price is at or below the target price, marks the alert as triggered.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class PriceAlertChecker {

    private final PriceAlertRepository  priceAlertRepository;
    private final PriceRecordRepository priceRecordRepository;

    /**
     * Runs every 5 minutes: "0 */5 * * * *"
     */
    @Scheduled(cron = "0 */5 * * * *")
    @Transactional
    public void checkAlerts() {
        List<PriceAlert> untriggeredAlerts = priceAlertRepository.findByTriggeredFalse();

        if (untriggeredAlerts.isEmpty()) {
            log.debug("PriceAlertChecker: no untriggered alerts to process");
            return;
        }

        log.debug("PriceAlertChecker: checking {} untriggered alerts", untriggeredAlerts.size());

        int triggeredCount = 0;
        for (PriceAlert alert : untriggeredAlerts) {
            try {
                Optional<PriceRecord> latestRecord = fetchLatestPrice(alert);

                if (latestRecord.isPresent()) {
                    PriceRecord record = latestRecord.get();
                    if (record.getPrice().compareTo(alert.getTargetPrice()) <= 0) {
                        alert.setTriggered(true);
                        alert.setTriggeredAt(LocalDateTime.now());
                        priceAlertRepository.save(alert);

                        log.info("Alert triggered for userId={} canonicalId={} platform={} " +
                                "targetPrice={} currentPrice={}",
                            alert.getUserId(), alert.getCanonicalId(), alert.getPlatform(),
                            alert.getTargetPrice(), record.getPrice());

                        triggeredCount++;
                    }
                } else {
                    log.debug("PriceAlertChecker: no price record found for alertId={} " +
                              "canonicalId={} platform={}",
                        alert.getId(), alert.getCanonicalId(), alert.getPlatform());
                }
            } catch (Exception e) {
                log.error("PriceAlertChecker: error processing alertId={}: {}",
                    alert.getId(), e.getMessage(), e);
            }
        }

        if (triggeredCount > 0) {
            log.info("PriceAlertChecker: triggered {} alerts in this run", triggeredCount);
        }
    }

    private Optional<PriceRecord> fetchLatestPrice(PriceAlert alert) {
        if (alert.getPlatform() != null && !alert.getPlatform().isBlank()) {
            return priceRecordRepository
                .findFirstByCanonicalIdAndPlatformOrderByRecordedAtDesc(
                    alert.getCanonicalId(), alert.getPlatform());
        }
        // If no platform specified, get the lowest current price across all platforms
        List<PriceRecord> latestPerPlatform = priceRecordRepository
            .findLatestPricePerPlatform(alert.getCanonicalId());
        return latestPerPlatform.stream()
            .min((a, b) -> a.getPrice().compareTo(b.getPrice()));
    }
}
