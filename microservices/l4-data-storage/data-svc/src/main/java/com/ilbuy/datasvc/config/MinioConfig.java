package com.ilbuy.datasvc.config;

import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MinioConfig {

    @Value("${ilbuy.minio.endpoint:http://minio:9000}")
    private String endpoint;

    @Value("${ilbuy.minio.access-key:minioadmin}")
    private String accessKey;

    @Value("${ilbuy.minio.secret-key:minioadmin}")
    private String secretKey;

    @Bean
    public MinioClient minioClient() {
        return MinioClient.builder()
            .endpoint(endpoint)
            .credentials(accessKey, secretKey)
            .build();
    }
}
