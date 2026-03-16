package com.ilbuy.format.storage;

import io.minio.*;
import io.minio.http.Method;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.concurrent.TimeUnit;

/**
 * MinIO object storage service.
 * Handles upload and pre-signed URL generation for HTML, PDF, Excel reports.
 */
@Service
@Slf4j
public class MinioStorageService {

    private final MinioClient minioClient;

    @Value("${minio.bucket.html}")
    private String htmlBucket;

    @Value("${minio.bucket.pdf}")
    private String pdfBucket;

    @Value("${minio.bucket.excel}")
    private String excelBucket;

    @Value("${minio.url-expiry-hours:72}")
    private int urlExpiryHours;

    public MinioStorageService(@Value("${minio.endpoint}") String endpoint,
                               @Value("${minio.access-key}") String accessKey,
                               @Value("${minio.secret-key}") String secretKey) {
        this.minioClient = MinioClient.builder()
                .endpoint(endpoint)
                .credentials(accessKey, secretKey)
                .build();
    }

    /**
     * Ensures required buckets exist on startup.
     */
    public void ensureBucketsExist() {
        for (String bucket : new String[]{htmlBucket, pdfBucket, excelBucket}) {
            ensureBucket(bucket);
        }
    }

    private void ensureBucket(String bucket) {
        try {
            boolean exists = minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
            if (!exists) {
                minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
                log.info("[MinIO] Created bucket: {}", bucket);
            }
        } catch (Exception e) {
            log.warn("[MinIO] Could not ensure bucket '{}': {}", bucket, e.getMessage());
        }
    }

    public String uploadHtml(String objectKey, byte[] content) {
        return upload(htmlBucket, objectKey, content, "text/html; charset=UTF-8");
    }

    public String uploadPdf(String objectKey, byte[] content) {
        return upload(pdfBucket, objectKey, content, "application/pdf");
    }

    public String uploadExcel(String objectKey, byte[] content) {
        return upload(excelBucket, objectKey, content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    }

    private String upload(String bucket, String key, byte[] content, String contentType) {
        try (InputStream is = new ByteArrayInputStream(content)) {
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(bucket)
                    .object(key)
                    .stream(is, content.length, -1)
                    .contentType(contentType)
                    .build());
            log.info("[MinIO] Uploaded {}/{} ({} bytes)", bucket, key, content.length);
            return generatePresignedUrl(bucket, key);
        } catch (Exception e) {
            log.error("[MinIO] Upload failed for {}/{}: {}", bucket, key, e.getMessage(), e);
            throw new RuntimeException("MinIO upload failed: " + e.getMessage(), e);
        }
    }

    public String generatePresignedUrl(String bucket, String key) {
        try {
            return minioClient.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                    .bucket(bucket)
                    .object(key)
                    .method(Method.GET)
                    .expiry(urlExpiryHours, TimeUnit.HOURS)
                    .build());
        } catch (Exception e) {
            log.error("[MinIO] URL generation failed for {}/{}: {}", bucket, key, e.getMessage());
            return null;
        }
    }

    public void delete(String bucket, String key) {
        try {
            minioClient.removeObject(RemoveObjectArgs.builder().bucket(bucket).object(key).build());
            log.info("[MinIO] Deleted {}/{}", bucket, key);
        } catch (Exception e) {
            log.warn("[MinIO] Delete failed for {}/{}: {}", bucket, key, e.getMessage());
        }
    }
}
