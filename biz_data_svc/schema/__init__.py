"""数据库 Schema 初始化"""
import os
from ..common.db import Database


def init_schema(db: Database) -> None:
    """执行 schema.sql 初始化所有表"""
    sql_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(sql_path, encoding='utf-8') as f:
        sql = f.read()
    # SQLite executescript 不支持参数化，直接执行
    db.conn.executescript(sql)
