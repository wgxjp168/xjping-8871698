"""
B端采购模块（m04_procurement）
导出所有领域模型和 Repository 类。
"""
from .models import (
    PurchaseRequest,
    PurchaseRequestItem,
    ApprovalWorkflow,
    ApprovalNode,
    ApprovalInstance,
    ApprovalRecord,
    SourcingEvent,
    SourcingQuote,
    Contract,
)
from .purchase_repository import PurchaseRepository
from .approval_repository import ApprovalRepository
from .sourcing_repository import SourcingRepository
from .contract_repository import ContractRepository

__all__ = [
    # 领域模型
    'PurchaseRequest',
    'PurchaseRequestItem',
    'ApprovalWorkflow',
    'ApprovalNode',
    'ApprovalInstance',
    'ApprovalRecord',
    'SourcingEvent',
    'SourcingQuote',
    'Contract',
    # Repository
    'PurchaseRepository',
    'ApprovalRepository',
    'SourcingRepository',
    'ContractRepository',
]
