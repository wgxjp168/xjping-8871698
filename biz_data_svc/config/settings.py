"""
应用配置管理
支持从环境变量覆盖默认值
"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # 数据库
    db_path: str = field(default_factory=lambda: os.getenv('DB_PATH', 'biz_mall.db'))
    db_echo:  bool = field(default_factory=lambda: os.getenv('DB_ECHO', '0') == '1')

    # 分页
    default_page_size: int = 20
    max_page_size:     int = 200

    # 密码策略（仅做格式校验，真实项目请使用 bcrypt 等）
    password_min_len: int = 6

    # 库存预警阈值
    stock_warning_threshold: int = 10

    # 促销折扣下限（不允许折扣低于此值）
    min_discount_rate: float = 0.01


# 全局单例
settings = Settings()
