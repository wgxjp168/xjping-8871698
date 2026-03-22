"""
MinIO 对象存储客户端封装
职责：
  1. 存储生成的报告 PDF/HTML（Bucket: ilbuy-reports）
  2. 用户上传的图片（Bucket: ilbuy-images）
  3. 电子合同文件（Bucket: ilbuy-contracts）
  4. 通过预签名 URL 实现安全的上传与下载
设计要点：
  - 上传 URL 有效期 1 小时
  - 下载 URL 有效期 24 小时
  - 按业务类型隔离 Bucket，每个 Bucket 启用版本控制
"""
from __future__ import annotations

import io
import logging
import os
from datetime import timedelta
from typing import Dict, Optional, Tuple

try:
    from minio import Minio
    from minio.error import S3Error
    _MINIO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MINIO_AVAILABLE = False

from ..config.settings import Settings

logger = logging.getLogger(__name__)

# Bucket -> 存储策略描述
BUCKET_META: Dict[str, str] = {
    'ilbuy-reports':   '报告文件（PDF/HTML）',
    'ilbuy-images':    '用户/商品图片',
    'ilbuy-contracts': '电子合同',
}


class MinioClient:
    """
    MinIO 客户端，惰性初始化。
    不可用时降级（返回 None / False），业务层自行处理降级策略。
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._cfg = settings or Settings()
        self._client: Optional[Any] = None

    # ------------------------------------------------------------------ #
    #  连接管理 & Bucket 初始化                                            #
    # ------------------------------------------------------------------ #

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not _MINIO_AVAILABLE:
            logger.warning('minio-py 未安装，MinIO 功能不可用')
            return None
        try:
            self._client = Minio(
                endpoint=self._cfg.minio_endpoint,
                access_key=self._cfg.minio_access_key,
                secret_key=self._cfg.minio_secret_key,
                secure=self._cfg.minio_secure,
            )
            logger.info('MinIO 连接成功，endpoint: %s', self._cfg.minio_endpoint)
        except Exception as exc:
            logger.error('MinIO 连接失败: %s', exc)
            self._client = None
        return self._client

    def ensure_buckets(self) -> bool:
        """确保所有业务 Bucket 存在，不存在则创建。"""
        c = self._get_client()
        if not c:
            return False
        buckets = [
            self._cfg.minio_bucket_reports,
            self._cfg.minio_bucket_images,
            self._cfg.minio_bucket_contracts,
        ]
        ok = True
        for bucket in buckets:
            try:
                if not c.bucket_exists(bucket):
                    c.make_bucket(bucket)
                    logger.info('Bucket %s 创建成功（%s）', bucket, BUCKET_META.get(bucket, ''))
            except S3Error as exc:
                logger.error('ensure_buckets 失败 bucket=%s: %s', bucket, exc)
                ok = False
        return ok

    # ------------------------------------------------------------------ #
    #  上传操作                                                            #
    # ------------------------------------------------------------------ #

    def upload_bytes(self, bucket: str, object_name: str,
                     data: bytes, content_type: str = 'application/octet-stream') -> bool:
        """
        上传字节流到指定 Bucket / Object。
        适用于服务端直接生成的报告、合同等。
        """
        c = self._get_client()
        if not c:
            return False
        try:
            stream = io.BytesIO(data)
            c.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=stream,
                length=len(data),
                content_type=content_type,
            )
            logger.debug('upload_bytes 成功: %s/%s (%d bytes)', bucket, object_name, len(data))
            return True
        except S3Error as exc:
            logger.error('upload_bytes 失败 %s/%s: %s', bucket, object_name, exc)
            return False

    def upload_file(self, bucket: str, object_name: str, file_path: str,
                    content_type: str = 'application/octet-stream') -> bool:
        """上传本地文件到 MinIO。"""
        c = self._get_client()
        if not c:
            return False
        if not os.path.exists(file_path):
            logger.error('upload_file: 文件不存在 %s', file_path)
            return False
        try:
            c.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )
            return True
        except S3Error as exc:
            logger.error('upload_file 失败 %s/%s: %s', bucket, object_name, exc)
            return False

    # ------------------------------------------------------------------ #
    #  预签名 URL（安全上传 / 下载）                                       #
    # ------------------------------------------------------------------ #

    def presigned_upload_url(self, bucket: str, object_name: str,
                             expire_s: Optional[int] = None) -> Optional[str]:
        """
        生成预签名上传 URL（PUT），有效期默认 1 小时。
        前端直接向 MinIO 上传，无需经过应用服务器。
        """
        c = self._get_client()
        if not c:
            return None
        if expire_s is None:
            expire_s = self._cfg.minio_presign_upload_expire
        try:
            url = c.presigned_put_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(seconds=expire_s),
            )
            return url
        except S3Error as exc:
            logger.error('presigned_upload_url 失败 %s/%s: %s', bucket, object_name, exc)
            return None

    def presigned_download_url(self, bucket: str, object_name: str,
                               expire_s: Optional[int] = None) -> Optional[str]:
        """
        生成预签名下载 URL（GET），有效期默认 24 小时。
        """
        c = self._get_client()
        if not c:
            return None
        if expire_s is None:
            expire_s = self._cfg.minio_presign_download_expire
        try:
            url = c.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(seconds=expire_s),
            )
            return url
        except S3Error as exc:
            logger.error('presigned_download_url 失败 %s/%s: %s', bucket, object_name, exc)
            return None

    # ------------------------------------------------------------------ #
    #  下载 / 读取                                                         #
    # ------------------------------------------------------------------ #

    def download_bytes(self, bucket: str, object_name: str) -> Optional[bytes]:
        """从 MinIO 读取文件内容为字节流。"""
        c = self._get_client()
        if not c:
            return None
        try:
            resp = c.get_object(bucket, object_name)
            return resp.read()
        except S3Error as exc:
            logger.error('download_bytes 失败 %s/%s: %s', bucket, object_name, exc)
            return None

    def download_file(self, bucket: str, object_name: str, dest_path: str) -> bool:
        """下载文件到本地路径。"""
        c = self._get_client()
        if not c:
            return False
        try:
            c.fget_object(bucket, object_name, dest_path)
            return True
        except S3Error as exc:
            logger.error('download_file 失败 %s/%s: %s', bucket, object_name, exc)
            return False

    # ------------------------------------------------------------------ #
    #  删除 & 元数据                                                       #
    # ------------------------------------------------------------------ #

    def delete_object(self, bucket: str, object_name: str) -> bool:
        """删除对象。"""
        c = self._get_client()
        if not c:
            return False
        try:
            c.remove_object(bucket, object_name)
            return True
        except S3Error as exc:
            logger.error('delete_object 失败 %s/%s: %s', bucket, object_name, exc)
            return False

    def object_exists(self, bucket: str, object_name: str) -> bool:
        """检查对象是否存在。"""
        c = self._get_client()
        if not c:
            return False
        try:
            c.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False

    def get_object_meta(self, bucket: str, object_name: str) -> Optional[Dict]:
        """获取对象元数据（大小、Content-Type、ETag 等）。"""
        c = self._get_client()
        if not c:
            return None
        try:
            stat = c.stat_object(bucket, object_name)
            return {
                'size':         stat.size,
                'content_type': stat.content_type,
                'etag':         stat.etag,
                'last_modified': str(stat.last_modified),
            }
        except S3Error as exc:
            logger.error('get_object_meta 失败 %s/%s: %s', bucket, object_name, exc)
            return None

    # ------------------------------------------------------------------ #
    #  业务快捷方法                                                         #
    # ------------------------------------------------------------------ #

    def upload_report(self, report_id: str, data: bytes,
                      fmt: str = 'pdf') -> Optional[str]:
        """
        上传报告文件，返回预签名下载 URL。
        object_name: reports/<report_id>.<fmt>
        """
        object_name = f'reports/{report_id}.{fmt}'
        content_type = 'application/pdf' if fmt == 'pdf' else 'text/html'
        ok = self.upload_bytes(self._cfg.minio_bucket_reports, object_name, data, content_type)
        return self.presigned_download_url(self._cfg.minio_bucket_reports, object_name) if ok else None

    def get_image_upload_url(self, user_id: int, filename: str) -> Optional[str]:
        """
        为用户图片上传生成预签名 URL。
        object_name: images/<user_id>/<filename>
        """
        object_name = f'images/{user_id}/{filename}'
        return self.presigned_upload_url(self._cfg.minio_bucket_images, object_name)

    def upload_contract(self, contract_id: str, data: bytes) -> Optional[str]:
        """
        上传电子合同 PDF，返回预签名下载 URL。
        object_name: contracts/<contract_id>.pdf
        """
        object_name = f'contracts/{contract_id}.pdf'
        ok = self.upload_bytes(self._cfg.minio_bucket_contracts, object_name, data, 'application/pdf')
        return self.presigned_download_url(self._cfg.minio_bucket_contracts, object_name) if ok else None


# 解决 Optional[Any] 在 _MINIO_AVAILABLE=False 时的 NameError
from typing import Any
