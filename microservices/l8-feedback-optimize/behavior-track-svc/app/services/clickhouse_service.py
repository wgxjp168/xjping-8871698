import logging
import uuid
from datetime import datetime
from typing import Optional
from clickhouse_driver import Client
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: Optional[Client] = None
_stub_mode = False


def get_client() -> Optional[Client]:
    global _client, _stub_mode
    if _stub_mode:
        return None
    if _client is None:
        try:
            _client = Client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                database=settings.clickhouse_db,
                user=settings.clickhouse_user,
                password=settings.clickhouse_password,
                connect_timeout=5,
            )
            _ensure_tables()
            logger.info("ClickHouse connected: %s:%d", settings.clickhouse_host, settings.clickhouse_port)
        except Exception as e:
            logger.warning("ClickHouse unavailable (%s), switching to stub mode", e)
            _stub_mode = True
    return _client


def _ensure_tables():
    c = _client
    c.execute("""
        CREATE TABLE IF NOT EXISTS ilbuy_analytics.behavior_events (
            event_id     String,
            event_type   String,
            user_id      String,
            session_id   String,
            channel      LowCardinality(String),
            report_id    String,
            item_id      String,
            page_url     String,
            extra        String,
            event_time   DateTime
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(event_time)
        ORDER BY (user_id, event_time)
        TTL event_time + INTERVAL 365 DAY
    """)
    logger.info("ClickHouse table behavior_events ensured")


def insert_event(
    event_type: str,
    user_id: str,
    session_id: str,
    channel: str,
    report_id: str = "",
    item_id: str = "",
    page_url: str = "",
    extra: str = "{}",
    event_time: Optional[datetime] = None,
) -> str:
    event_id = str(uuid.uuid4())
    event_time = event_time or datetime.utcnow()
    client = get_client()
    if client is None:
        logger.debug("Stub mode: skipping ClickHouse insert event_type=%s", event_type)
        return event_id
    try:
        client.execute(
            """INSERT INTO ilbuy_analytics.behavior_events
               (event_id, event_type, user_id, session_id, channel,
                report_id, item_id, page_url, extra, event_time)
               VALUES""",
            [(event_id, event_type, user_id, session_id, channel,
              report_id, item_id, page_url, extra, event_time)],
        )
    except Exception as e:
        logger.error("ClickHouse insert error: %s", e)
    return event_id


def insert_batch(rows: list[dict]) -> int:
    """Batch insert of behavior events. Returns number of inserted rows."""
    client = get_client()
    if client is None or not rows:
        return 0
    try:
        data = [
            (
                str(uuid.uuid4()),
                r.get("event_type", ""),
                r.get("user_id", ""),
                r.get("session_id", ""),
                r.get("channel", ""),
                r.get("report_id", ""),
                r.get("item_id", ""),
                r.get("page_url", ""),
                str(r.get("extra") or "{}"),
                r.get("event_time") or datetime.utcnow(),
            )
            for r in rows
        ]
        client.execute(
            """INSERT INTO ilbuy_analytics.behavior_events
               (event_id, event_type, user_id, session_id, channel,
                report_id, item_id, page_url, extra, event_time)
               VALUES""",
            data,
        )
        return len(data)
    except Exception as e:
        logger.error("ClickHouse batch insert error: %s", e)
        return 0


def query_conversion_metrics(report_id: str) -> dict:
    """Query ClickHouse for report conversion funnel metrics."""
    client = get_client()
    if client is None:
        return {"view": 0, "detail": 0, "cart": 0, "purchase": 0}
    try:
        result = client.execute(
            """
            SELECT event_type, count() as cnt
            FROM ilbuy_analytics.behavior_events
            WHERE report_id = %(report_id)s
              AND event_type IN ('REPORT_VIEW', 'CONVERSION', 'CLICK', 'RECOMMENDATION_CLICK')
            GROUP BY event_type
            """,
            {"report_id": report_id},
        )
        return {row[0]: row[1] for row in result}
    except Exception as e:
        logger.error("ClickHouse query error: %s", e)
        return {}


def aggregate_behavior_summary(period_start: datetime, period_end: datetime) -> dict:
    """Aggregate behavior data for model feature engineering."""
    client = get_client()
    if client is None:
        return {"total_events": 0, "unique_users": 0, "top_reports": []}
    try:
        result = client.execute(
            """
            SELECT
                count() AS total_events,
                uniq(user_id) AS unique_users,
                groupArray(10)(report_id) AS top_reports
            FROM ilbuy_analytics.behavior_events
            WHERE event_time >= %(start)s AND event_time < %(end)s
              AND report_id != ''
            """,
            {"start": period_start, "end": period_end},
        )
        if result:
            row = result[0]
            return {"total_events": row[0], "unique_users": row[1], "top_reports": list(row[2])}
    except Exception as e:
        logger.error("ClickHouse aggregate error: %s", e)
    return {"total_events": 0, "unique_users": 0, "top_reports": []}
