"""
Elasticsearch 8.11 集群客户端封装
职责：
  1. 商品多维度检索与过滤（名称/分类/价格/标签/在售状态）
  2. 用户行为日志分析（点击/加购/下单/搜索关键词聚合）
  3. 商品索引管理（创建/更新/删除/批量同步）
设计要点：
  - 商品索引按类目分片（3 主分片，1 副本），_source 只保留必要字段
  - 行为日志索引按天滚动（ilbuy_behavior_logs-YYYY.MM.dd）
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from elasticsearch import Elasticsearch, helpers, NotFoundError, RequestError
    from elasticsearch.exceptions import ConnectionError as ESConnectionError
    _ES_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ES_AVAILABLE = False

from ..config.settings import Settings

logger = logging.getLogger(__name__)

# 商品索引 Mapping（只保留必要 _source 字段，减少存储）
PRODUCT_INDEX_MAPPING = {
    'settings': {
        'number_of_shards':   3,
        'number_of_replicas': 1,
        'analysis': {
            'analyzer': {
                'ik_smart_analyzer': {
                    'type':      'custom',
                    'tokenizer': 'ik_smart',
                }
            }
        }
    },
    'mappings': {
        '_source': {
            'includes': [
                'id', 'tenant_id', 'category_id', 'name', 'subtitle',
                'cover_image', 'unit', 'status', 'is_featured', 'tags',
                'sales_count', 'min_price', 'updated_at',
            ]
        },
        'properties': {
            'id':          {'type': 'long'},
            'tenant_id':   {'type': 'long'},
            'category_id': {'type': 'integer'},
            'name':        {'type': 'text', 'analyzer': 'ik_smart_analyzer',
                            'fields': {'keyword': {'type': 'keyword'}}},
            'subtitle':    {'type': 'text', 'analyzer': 'ik_smart_analyzer'},
            'cover_image': {'type': 'keyword', 'index': False},
            'unit':        {'type': 'keyword'},
            'status':      {'type': 'keyword'},
            'is_featured': {'type': 'boolean'},
            'tags':        {'type': 'text', 'analyzer': 'ik_smart_analyzer'},
            'sales_count': {'type': 'integer'},
            'min_price':   {'type': 'scaled_float', 'scaling_factor': 100},
            'updated_at':  {'type': 'date', 'format': 'strict_date_optional_time||epoch_millis'},
        }
    }
}

# 行为日志索引 Mapping
BEHAVIOR_LOG_INDEX_MAPPING = {
    'settings': {
        'number_of_shards':   1,
        'number_of_replicas': 1,
    },
    'mappings': {
        'properties': {
            'user_id':     {'type': 'long'},
            'tenant_id':   {'type': 'long'},
            'event_type':  {'type': 'keyword'},
            'product_id':  {'type': 'long'},
            'category_id': {'type': 'integer'},
            'keyword':     {'type': 'keyword'},
            'order_id':    {'type': 'long'},
            'amount':      {'type': 'scaled_float', 'scaling_factor': 100},
            'ip':          {'type': 'ip'},
            'ua':          {'type': 'keyword', 'index': False},
            'occurred_at': {'type': 'date', 'format': 'strict_date_optional_time||epoch_millis'},
        }
    }
}


class ESClient:
    """
    Elasticsearch 8 客户端，惰性初始化。
    不可用时降级（返回空结果），保证主业务不中断。
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._cfg = settings or Settings()
        self._client: Optional[Any] = None

    # ------------------------------------------------------------------ #
    #  连接管理                                                             #
    # ------------------------------------------------------------------ #

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not _ES_AVAILABLE:
            logger.warning('elasticsearch-py 未安装，ES 功能不可用')
            return None
        try:
            hosts = [h.strip() for h in self._cfg.es_hosts.split(',') if h.strip()]
            auth = (self._cfg.es_username, self._cfg.es_password) if self._cfg.es_password else None
            self._client = Elasticsearch(
                hosts=hosts,
                basic_auth=auth,
                verify_certs=self._cfg.es_verify_certs,
                request_timeout=10,
                max_retries=3,
                retry_on_timeout=True,
            )
            logger.info('Elasticsearch 连接成功，hosts: %s', hosts)
        except Exception as exc:
            logger.error('Elasticsearch 连接失败: %s', exc)
            self._client = None
        return self._client

    def ping(self) -> bool:
        c = self._get_client()
        try:
            return bool(c and c.ping())
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  商品索引管理                                                         #
    # ------------------------------------------------------------------ #

    def ensure_product_index(self) -> bool:
        """若索引不存在则创建（含 mapping）。"""
        c = self._get_client()
        if not c:
            return False
        idx = self._cfg.es_index_product
        try:
            if not c.indices.exists(index=idx):
                c.indices.create(index=idx, body=PRODUCT_INDEX_MAPPING)
                logger.info('商品索引 %s 创建成功', idx)
            return True
        except Exception as exc:
            logger.error('ensure_product_index 失败: %s', exc)
            return False

    def index_product(self, product: Dict[str, Any]) -> bool:
        """
        新增或更新商品文档。
        product 必须含 'id' 字段。
        """
        c = self._get_client()
        if not c:
            return False
        try:
            c.index(
                index=self._cfg.es_index_product,
                id=str(product['id']),
                document=product,
            )
            return True
        except Exception as exc:
            logger.error('index_product 失败 id=%s: %s', product.get('id'), exc)
            return False

    def bulk_index_products(self, products: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        批量索引商品。
        返回 (成功数, 失败数)。
        """
        c = self._get_client()
        if not c or not products:
            return 0, 0
        actions = [
            {
                '_index': self._cfg.es_index_product,
                '_id':    str(p['id']),
                '_source': p,
            }
            for p in products
        ]
        try:
            success, errors = helpers.bulk(c, actions, raise_on_error=False, stats_only=False)
            fail_cnt = len(errors) if isinstance(errors, list) else 0
            logger.info('bulk_index_products: 成功=%d 失败=%d', success, fail_cnt)
            return success, fail_cnt
        except Exception as exc:
            logger.error('bulk_index_products 失败: %s', exc)
            return 0, len(products)

    def delete_product(self, product_id: int) -> bool:
        """下架/删除商品时从索引移除。"""
        c = self._get_client()
        if not c:
            return False
        try:
            c.delete(index=self._cfg.es_index_product, id=str(product_id))
            return True
        except NotFoundError:
            return True   # 文档不存在也视为成功
        except Exception as exc:
            logger.error('delete_product 失败 id=%d: %s', product_id, exc)
            return False

    # ------------------------------------------------------------------ #
    #  商品检索                                                            #
    # ------------------------------------------------------------------ #

    def search_products(
        self,
        *,
        tenant_id: int,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        status: str = 'on_sale',
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = 'sales_count',   # sales_count | min_price | updated_at
        sort_order: str = 'desc',
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        """
        多维度商品检索，支持全文+过滤+价格区间+分页。
        返回 {'total': int, 'items': [...], 'took_ms': int}
        """
        c = self._get_client()
        if not c:
            return {'total': 0, 'items': [], 'took_ms': 0}

        must: List[Dict] = [{'term': {'tenant_id': tenant_id}}]
        if status:
            must.append({'term': {'status': status}})
        if category_id is not None:
            must.append({'term': {'category_id': category_id}})
        if is_featured is not None:
            must.append({'term': {'is_featured': is_featured}})

        should: List[Dict] = []
        if keyword:
            should = [
                {'match': {'name':     {'query': keyword, 'boost': 3.0}}},
                {'match': {'subtitle': {'query': keyword, 'boost': 1.5}}},
                {'match': {'tags':     {'query': keyword, 'boost': 1.0}}},
            ]
            must.append({'bool': {'should': should, 'minimum_should_match': 1}})

        if tags:
            must.append({'terms': {'tags': tags}})

        filter_clauses: List[Dict] = []
        if min_price is not None or max_price is not None:
            price_range: Dict = {}
            if min_price is not None:
                price_range['gte'] = min_price
            if max_price is not None:
                price_range['lte'] = max_price
            filter_clauses.append({'range': {'min_price': price_range}})

        query = {'bool': {'must': must, 'filter': filter_clauses or []}}
        body = {
            'query': query,
            'sort':  [{sort_by: {'order': sort_order}}],
            'from':  (page - 1) * size,
            'size':  size,
        }

        try:
            resp = c.search(index=self._cfg.es_index_product, body=body)
            hits = resp['hits']
            return {
                'total':   hits['total']['value'],
                'items':   [h['_source'] for h in hits['hits']],
                'took_ms': resp['took'],
            }
        except Exception as exc:
            logger.error('search_products 失败: %s', exc)
            return {'total': 0, 'items': [], 'took_ms': 0}

    # ------------------------------------------------------------------ #
    #  用户行为日志                                                         #
    # ------------------------------------------------------------------ #

    def _behavior_index_name(self, date: Optional[datetime] = None) -> str:
        """按天滚动索引名：ilbuy_behavior_logs-YYYY.MM.dd"""
        d = date or datetime.utcnow()
        return f"{self._cfg.es_index_behavior_log}-{d.strftime('%Y.%m.%d')}"

    def ensure_behavior_index(self, date: Optional[datetime] = None) -> bool:
        """若当天行为索引不存在则创建。"""
        c = self._get_client()
        if not c:
            return False
        idx = self._behavior_index_name(date)
        try:
            if not c.indices.exists(index=idx):
                c.indices.create(index=idx, body=BEHAVIOR_LOG_INDEX_MAPPING)
                logger.info('行为日志索引 %s 创建成功', idx)
            return True
        except Exception as exc:
            logger.error('ensure_behavior_index 失败: %s', exc)
            return False

    def log_behavior(self, event: Dict[str, Any]) -> bool:
        """
        写入一条行为日志。
        event 必须含 'user_id', 'event_type', 'occurred_at'。
        event_type: click | add_cart | order | search | feedback
        """
        c = self._get_client()
        if not c:
            return False
        occurred_at = event.get('occurred_at')
        dt = datetime.fromisoformat(occurred_at) if isinstance(occurred_at, str) else None
        idx = self._behavior_index_name(dt)
        try:
            c.index(index=idx, document=event)
            return True
        except Exception as exc:
            logger.error('log_behavior 失败: %s', exc)
            return False

    def bulk_log_behaviors(self, events: List[Dict[str, Any]]) -> Tuple[int, int]:
        """批量写入行为日志。返回 (成功数, 失败数)。"""
        c = self._get_client()
        if not c or not events:
            return 0, 0
        actions = []
        for ev in events:
            occurred_at = ev.get('occurred_at')
            dt = datetime.fromisoformat(occurred_at) if isinstance(occurred_at, str) else None
            actions.append({
                '_index':  self._behavior_index_name(dt),
                '_source': ev,
            })
        try:
            success, errors = helpers.bulk(c, actions, raise_on_error=False, stats_only=False)
            fail_cnt = len(errors) if isinstance(errors, list) else 0
            return success, fail_cnt
        except Exception as exc:
            logger.error('bulk_log_behaviors 失败: %s', exc)
            return 0, len(events)

    def analyze_hot_keywords(self, tenant_id: int,
                             start_date: str, end_date: str,
                             top_n: int = 20) -> List[Dict[str, Any]]:
        """
        聚合分析热搜词 Top-N（近 N 天内 search 类型事件）。
        返回 [{'keyword': str, 'count': int}, ...]
        """
        c = self._get_client()
        if not c:
            return []
        body = {
            'query': {
                'bool': {
                    'must': [
                        {'term':  {'tenant_id':  tenant_id}},
                        {'term':  {'event_type': 'search'}},
                        {'range': {'occurred_at': {'gte': start_date, 'lte': end_date}}},
                    ]
                }
            },
            'aggs': {
                'hot_keywords': {
                    'terms': {'field': 'keyword', 'size': top_n}
                }
            },
            'size': 0,
        }
        idx_pattern = f"{self._cfg.es_index_behavior_log}-*"
        try:
            resp = c.search(index=idx_pattern, body=body)
            buckets = resp['aggregations']['hot_keywords']['buckets']
            return [{'keyword': b['key'], 'count': b['doc_count']} for b in buckets]
        except Exception as exc:
            logger.error('analyze_hot_keywords 失败: %s', exc)
            return []

    def analyze_user_behavior(self, user_id: int,
                              days: int = 30) -> Dict[str, Any]:
        """
        分析单用户行为概况：各事件类型计数。
        返回 {'click': N, 'add_cart': N, 'order': N, 'search': N}
        """
        c = self._get_client()
        if not c:
            return {}
        body = {
            'query': {
                'bool': {
                    'must': [
                        {'term':  {'user_id': user_id}},
                        {'range': {'occurred_at': {'gte': f'now-{days}d/d'}}},
                    ]
                }
            },
            'aggs': {
                'by_event': {
                    'terms': {'field': 'event_type', 'size': 20}
                }
            },
            'size': 0,
        }
        idx_pattern = f"{self._cfg.es_index_behavior_log}-*"
        try:
            resp = c.search(index=idx_pattern, body=body)
            buckets = resp['aggregations']['by_event']['buckets']
            return {b['key']: b['doc_count'] for b in buckets}
        except Exception as exc:
            logger.error('analyze_user_behavior 失败: %s', exc)
            return {}
