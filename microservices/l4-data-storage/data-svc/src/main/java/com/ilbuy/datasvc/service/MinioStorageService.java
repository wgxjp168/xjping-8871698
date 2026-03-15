package com.ilbuy.datasvc.service;

import io.minio.*;
import io.minio.http.Method;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.concurrent.TimeUnit;

/**
 * MinIO 对象存储服务 — 商品图片存储
 *
 * Bucket 命名：ilbuy-product-images
 * Key 格式：  {platform}/{product_id}/{hash}.jpg
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class MinioStorageService {

    private final MinioClient minioClient;

    @Value("${ilbuy.minio.bucket:ilbuy-product-images}")
    private String bucket;

    /**
     * 上传图片 InputStream
     */
    public String uploadImage(String objectKey, InputStream inputStream,
                              long size, String contentType) {
        try {
            ensureBucket();
            minioClient.putObject(PutObjectArgs.builder()
                .bucket(bucket)
                .object(objectKey)
                .stream(inputStream, size, -1)
                .contentType(contentType)
                .build());
            log.debug("MinIO upload: bucket={} key={}", bucket, objectKey);
            return objectKey;
        } catch (Exception e) {
            log.error("MinIO upload failed key={}: {}", objectKey, e.getMessage());
            throw new RuntimeException("MinIO upload failed: " + e.getMessage(), e);
        }
    }

    /**
     * 获取预签名 URL（7天有效）
     */
    public String getPresignedUrl(String objectKey) {
        try {
            return minioClient.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                .bucket(bucket)
                .object(objectKey)
                .method(Method.GET)
                .expiry(7, TimeUnit.DAYS)
                .build());
        } catch (Exception e) {
            log.error("MinIO presign failed key={}: {}", objectKey, e.getMessage());
            return null;
        }
    }

    /**
     * 检查对象是否存在
     */
    public boolean exists(String objectKey) {
        try {
            minioClient.statObject(StatObjectArgs.builder()
                .bucket(bucket)
                .object(objectKey)
                .build());
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 删除对象
     */
    public void delete(String objectKey) {
        try {
            minioClient.removeObject(RemoveObjectArgs.builder()
                .bucket(bucket)
                .object(objectKey)
                .build());
        } catch (Exception e) {
            log.warn("MinIO delete failed key={}: {}", objectKey, e.getMessage());
        }
    }

    private void ensureBucket() throws Exception {
        boolean exists = minioClient.bucketExists(
            BucketExistsArgs.builder().bucket(bucket).build());
        if (!exists) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
            log.info("Created MinIO bucket: {}", bucket);
        }
    }
}
