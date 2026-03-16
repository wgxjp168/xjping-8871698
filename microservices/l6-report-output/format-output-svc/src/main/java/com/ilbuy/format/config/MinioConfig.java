package com.ilbuy.format.config;

import com.ilbuy.format.storage.MinioStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class MinioConfig {

    private final MinioStorageService minioStorageService;

    @EventListener(ApplicationReadyEvent.class)
    public void initBuckets() {
        log.info("[MinIO] Initializing storage buckets...");
        minioStorageService.ensureBucketsExist();
    }
}
