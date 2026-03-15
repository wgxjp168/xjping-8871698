package com.ilbuy.datasvc.canal;

import com.alibaba.otter.canal.client.CanalConnector;
import com.alibaba.otter.canal.client.CanalConnectors;
import com.alibaba.otter.canal.protocol.CanalEntry.*;
import com.alibaba.otter.canal.protocol.Message;
import com.ilbuy.datasvc.model.document.ProductDocument;
import com.ilbuy.datasvc.repository.es.ProductEsRepository;
import com.ilbuy.datasvc.repository.mysql.ProductRepository;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.net.InetSocketAddress;
import java.util.List;

/**
 * Canal Client — MySQL binlog 增量同步到 Elasticsearch
 *
 * 工作原理：
 *   Canal Server 订阅 MySQL binlog → Canal Client 拉取变更事件
 *   → 识别 products 表 INSERT/UPDATE/DELETE
 *   → 同步更新 ES index
 *
 * 配置开关：ilbuy.canal.enabled=true (默认 false，避免无 Canal Server 时启动失败)
 */
@Component
@ConditionalOnProperty(name = "ilbuy.canal.enabled", havingValue = "true")
@RequiredArgsConstructor
@Slf4j
public class CanalSyncHandler {

    @Value("${ilbuy.canal.host:localhost}")
    private String canalHost;

    @Value("${ilbuy.canal.port:11111}")
    private int canalPort;

    @Value("${ilbuy.canal.destination:ilbuy_canal}")
    private String destination;

    @Value("${ilbuy.canal.filter:ilbuy\\.products}")
    private String filter;

    private final ProductEsRepository  esRepository;
    private final ProductRepository    productRepository;

    private CanalConnector connector;
    private volatile boolean running = false;

    @PostConstruct
    public void start() {
        connector = CanalConnectors.newSingleConnector(
            new InetSocketAddress(canalHost, canalPort),
            destination, "", ""
        );
        running = true;
        startPollingAsync();
        log.info("\"Canal sync handler started: {}:{} destination={}\"",
            canalHost, canalPort, destination);
    }

    @PreDestroy
    public void stop() {
        running = false;
        if (connector != null) {
            connector.disconnect();
        }
        log.info("\"Canal sync handler stopped\"");
    }

    @Async
    public void startPollingAsync() {
        try {
            connector.connect();
            connector.subscribe(filter);
            connector.rollback();

            while (running) {
                Message message = connector.getWithoutAck(100);  // batch size 100
                long batchId = message.getId();
                List<Entry> entries = message.getEntries();

                if (batchId == -1 || entries.isEmpty()) {
                    Thread.sleep(500);
                    continue;
                }

                for (Entry entry : entries) {
                    processEntry(entry);
                }

                connector.ack(batchId);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.info("Canal polling interrupted");
        } catch (Exception e) {
            log.error("Canal polling error: {}", e.getMessage(), e);
            if (running) {
                try { Thread.sleep(5000); } catch (InterruptedException ie) { Thread.currentThread().interrupt(); }
                startPollingAsync();  // reconnect
            }
        }
    }

    private void processEntry(Entry entry) {
        if (entry.getEntryType() != EntryType.ROWDATA) return;

        RowChange rowChange;
        try {
            rowChange = RowChange.parseFrom(entry.getStoreValue());
        } catch (Exception e) {
            log.error("Canal parse error: {}", e.getMessage());
            return;
        }

        EventType eventType = rowChange.getEventType();
        String table = entry.getHeader().getTableName();

        if (!"products".equals(table)) return;

        log.debug("Canal event: table={} type={}", table, eventType);

        for (RowData rowData : rowChange.getRowDatasList()) {
            switch (eventType) {
                case INSERT, UPDATE -> syncUpsert(rowData.getAfterColumnsList());
                case DELETE         -> syncDelete(rowData.getBeforeColumnsList());
                default -> {}
            }
        }
    }

    private void syncUpsert(List<Column> columns) {
        String canonicalId = getColumn(columns, "canonical_id");
        if (canonicalId == null) return;

        productRepository.findByCanonicalId(canonicalId).ifPresent(product -> {
            ProductDocument doc = ProductDocument.builder()
                .canonicalId(product.getCanonicalId())
                .platform(product.getPlatform())
                .productId(product.getProductId())
                .title(product.getTitle())
                .titleCleaned(product.getTitleCleaned())
                .price(product.getPrice())
                .originalPrice(product.getOriginalPrice())
                .discountPct(product.getDiscountPct())
                .brandNormalised(product.getBrandNormalised())
                .salesCount(product.getSalesCount())
                .reviewCount(product.getReviewCount())
                .averageRating(product.getAverageRating())
                .inStock(product.getInStock())
                .totalScore(product.getTotalScore())
                .grade(product.getGrade())
                .priceScore(product.getPriceScore())
                .popularityScore(product.getPopularityScore())
                .ratingScore(product.getRatingScore())
                .availabilityScore(product.getAvailabilityScore())
                .valueForMoneyScore(product.getValueForMoneyScore())
                .url(product.getUrl())
                .crawledAt(product.getCrawledAt())
                .updatedAt(java.time.Instant.now())
                .build();

            esRepository.save(doc);
            log.debug("Canal → ES upsert: {}", canonicalId);
        });
    }

    private void syncDelete(List<Column> columns) {
        String canonicalId = getColumn(columns, "canonical_id");
        if (canonicalId != null) {
            esRepository.deleteById(canonicalId);
            log.debug("Canal → ES delete: {}", canonicalId);
        }
    }

    private String getColumn(List<Column> columns, String name) {
        return columns.stream()
            .filter(c -> name.equals(c.getName()))
            .map(Column::getValue)
            .findFirst()
            .orElse(null);
    }
}
