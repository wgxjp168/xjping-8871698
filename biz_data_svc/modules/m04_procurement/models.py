"""
B端采购模块 — 领域模型
涉及表：purchase_requests, purchase_request_items, approval_workflows,
        approval_nodes, approval_instances, approval_records,
        sourcing_events, sourcing_quotes, contracts
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
#  PurchaseRequest                                                             #
# --------------------------------------------------------------------------- #

@dataclass
class PurchaseRequest:
    """采购申请主表"""
    tenant_id: int
    req_no: str
    title: str
    requester_id: int
    budget: float
    priority: str
    id: Optional[int] = None
    dept: str = ''
    category: str = ''
    currency: str = 'CNY'
    required_date: Optional[str] = None
    reason: str = ''
    status: str = 'draft'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    items: List['PurchaseRequestItem'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'req_no': self.req_no,
            'title': self.title,
            'requester_id': self.requester_id,
            'dept': self.dept,
            'category': self.category,
            'budget': self.budget,
            'currency': self.currency,
            'priority': self.priority,
            'required_date': self.required_date,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'items': [i.to_dict() for i in self.items],
        }

    @staticmethod
    def from_row(row) -> 'PurchaseRequest':
        """
        列顺序：id,tenant_id,req_no,title,requester_id,dept,category,
                budget,currency,priority,required_date,reason,status,
                created_at,updated_at
        """
        r = tuple(row)
        return PurchaseRequest(
            id=r[0],
            tenant_id=r[1],
            req_no=r[2],
            title=r[3],
            requester_id=r[4],
            dept=r[5],
            category=r[6],
            budget=r[7],
            currency=r[8],
            priority=r[9],
            required_date=r[10],
            reason=r[11],
            status=r[12],
            created_at=r[13],
            updated_at=r[14],
        )


# --------------------------------------------------------------------------- #
#  PurchaseRequestItem                                                         #
# --------------------------------------------------------------------------- #

@dataclass
class PurchaseRequestItem:
    """采购申请明细行"""
    request_id: int
    product_name: str
    quantity: float
    unit: str
    estimated_price: float
    id: Optional[int] = None
    spec: str = ''
    note: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'request_id': self.request_id,
            'product_name': self.product_name,
            'spec': self.spec,
            'quantity': self.quantity,
            'unit': self.unit,
            'estimated_price': self.estimated_price,
            'note': self.note,
        }

    @staticmethod
    def from_row(row) -> 'PurchaseRequestItem':
        """
        列顺序：id,request_id,product_name,spec,quantity,unit,
                estimated_price,note
        """
        r = tuple(row)
        return PurchaseRequestItem(
            id=r[0],
            request_id=r[1],
            product_name=r[2],
            spec=r[3],
            quantity=r[4],
            unit=r[5],
            estimated_price=r[6],
            note=r[7],
        )


# --------------------------------------------------------------------------- #
#  ApprovalWorkflow                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class ApprovalWorkflow:
    """审批流程定义"""
    tenant_id: int
    name: str
    business_type: str
    id: Optional[int] = None
    status: str = 'active'
    is_default: int = 0
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'business_type': self.business_type,
            'status': self.status,
            'is_default': self.is_default,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'ApprovalWorkflow':
        """
        列顺序：id,tenant_id,name,business_type,status,is_default,created_at
        """
        r = tuple(row)
        return ApprovalWorkflow(
            id=r[0],
            tenant_id=r[1],
            name=r[2],
            business_type=r[3],
            status=r[4],
            is_default=r[5],
            created_at=r[6],
        )


# --------------------------------------------------------------------------- #
#  ApprovalNode                                                                #
# --------------------------------------------------------------------------- #

@dataclass
class ApprovalNode:
    """审批流程节点"""
    workflow_id: int
    node_name: str
    node_type: str
    approver_ids: str       # JSON/CSV 存储
    sort_order: int
    id: Optional[int] = None
    condition_expr: str = ''
    action_type: str = 'any'        # any / all

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'node_name': self.node_name,
            'node_type': self.node_type,
            'approver_ids': self.approver_ids,
            'sort_order': self.sort_order,
            'condition_expr': self.condition_expr,
            'action_type': self.action_type,
        }

    @staticmethod
    def from_row(row) -> 'ApprovalNode':
        """
        列顺序：id,workflow_id,node_name,node_type,approver_ids,
                sort_order,condition_expr,action_type
        """
        r = tuple(row)
        return ApprovalNode(
            id=r[0],
            workflow_id=r[1],
            node_name=r[2],
            node_type=r[3],
            approver_ids=r[4],
            sort_order=r[5],
            condition_expr=r[6],
            action_type=r[7],
        )


# --------------------------------------------------------------------------- #
#  ApprovalInstance                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class ApprovalInstance:
    """审批实例（某单据的一次审批过程）"""
    workflow_id: int
    business_type: str
    business_id: int
    id: Optional[int] = None
    current_node: int = 1
    status: str = 'pending'
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    completed_by: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'business_type': self.business_type,
            'business_id': self.business_id,
            'current_node': self.current_node,
            'status': self.status,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'completed_by': self.completed_by,
        }

    @staticmethod
    def from_row(row) -> 'ApprovalInstance':
        """
        列顺序：id,workflow_id,business_type,business_id,current_node,
                status,started_at,completed_at,completed_by
        """
        r = tuple(row)
        return ApprovalInstance(
            id=r[0],
            workflow_id=r[1],
            business_type=r[2],
            business_id=r[3],
            current_node=r[4],
            status=r[5],
            started_at=r[6],
            completed_at=r[7],
            completed_by=r[8],
        )


# --------------------------------------------------------------------------- #
#  ApprovalRecord                                                              #
# --------------------------------------------------------------------------- #

@dataclass
class ApprovalRecord:
    """审批操作记录"""
    instance_id: int
    node_id: int
    node_order: int
    approver_id: int
    action: str
    id: Optional[int] = None
    comment: str = ''
    attachments: str = ''   # JSON/CSV 存储
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'node_id': self.node_id,
            'node_order': self.node_order,
            'approver_id': self.approver_id,
            'action': self.action,
            'comment': self.comment,
            'attachments': self.attachments,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'ApprovalRecord':
        """
        列顺序：id,instance_id,node_id,node_order,approver_id,
                action,comment,attachments,created_at
        """
        r = tuple(row)
        return ApprovalRecord(
            id=r[0],
            instance_id=r[1],
            node_id=r[2],
            node_order=r[3],
            approver_id=r[4],
            action=r[5],
            comment=r[6],
            attachments=r[7],
            created_at=r[8],
        )


# --------------------------------------------------------------------------- #
#  SourcingEvent                                                               #
# --------------------------------------------------------------------------- #

@dataclass
class SourcingEvent:
    """寻源/招标事件"""
    tenant_id: int
    event_no: str
    title: str
    id: Optional[int] = None
    request_id: Optional[int] = None
    description: str = ''
    deadline: Optional[str] = None
    status: str = 'draft'
    winner_supplier_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'request_id': self.request_id,
            'event_no': self.event_no,
            'title': self.title,
            'description': self.description,
            'deadline': self.deadline,
            'status': self.status,
            'winner_supplier_id': self.winner_supplier_id,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'SourcingEvent':
        """
        列顺序：id,tenant_id,request_id,event_no,title,description,
                deadline,status,winner_supplier_id,created_by,
                created_at,updated_at
        """
        r = tuple(row)
        return SourcingEvent(
            id=r[0],
            tenant_id=r[1],
            request_id=r[2],
            event_no=r[3],
            title=r[4],
            description=r[5],
            deadline=r[6],
            status=r[7],
            winner_supplier_id=r[8],
            created_by=r[9],
            created_at=r[10],
            updated_at=r[11],
        )


# --------------------------------------------------------------------------- #
#  SourcingQuote                                                               #
# --------------------------------------------------------------------------- #

@dataclass
class SourcingQuote:
    """供应商报价"""
    event_id: int
    supplier_id: int
    unit_price: float
    total_price: float
    delivery_days: int
    id: Optional[int] = None
    currency: str = 'CNY'
    warranty_months: int = 0
    note: str = ''
    attachments: str = ''   # JSON/CSV 存储
    is_winner: int = 0
    submitted_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'event_id': self.event_id,
            'supplier_id': self.supplier_id,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'currency': self.currency,
            'delivery_days': self.delivery_days,
            'warranty_months': self.warranty_months,
            'note': self.note,
            'attachments': self.attachments,
            'is_winner': self.is_winner,
            'submitted_at': self.submitted_at,
        }

    @staticmethod
    def from_row(row) -> 'SourcingQuote':
        """
        列顺序：id,event_id,supplier_id,unit_price,total_price,currency,
                delivery_days,warranty_months,note,attachments,
                is_winner,submitted_at
        """
        r = tuple(row)
        return SourcingQuote(
            id=r[0],
            event_id=r[1],
            supplier_id=r[2],
            unit_price=r[3],
            total_price=r[4],
            currency=r[5],
            delivery_days=r[6],
            warranty_months=r[7],
            note=r[8],
            attachments=r[9],
            is_winner=r[10],
            submitted_at=r[11],
        )


# --------------------------------------------------------------------------- #
#  Contract                                                                    #
# --------------------------------------------------------------------------- #

@dataclass
class Contract:
    """合同"""
    tenant_id: int
    contract_no: str
    title: str
    contract_type: str
    party_a: str
    party_b: str
    amount: float
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    sourcing_id: Optional[int] = None
    currency: str = 'CNY'
    sign_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    payment_terms: str = ''
    status: str = 'draft'
    file_url: str = ''
    signed_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'contract_no': self.contract_no,
            'title': self.title,
            'contract_type': self.contract_type,
            'party_a': self.party_a,
            'party_b': self.party_b,
            'supplier_id': self.supplier_id,
            'sourcing_id': self.sourcing_id,
            'amount': self.amount,
            'currency': self.currency,
            'sign_date': self.sign_date,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'payment_terms': self.payment_terms,
            'status': self.status,
            'file_url': self.file_url,
            'signed_by': self.signed_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'Contract':
        """
        列顺序：id,tenant_id,contract_no,title,contract_type,party_a,party_b,
                supplier_id,sourcing_id,amount,currency,sign_date,start_date,
                end_date,payment_terms,status,file_url,signed_by,
                created_at,updated_at
        """
        r = tuple(row)
        return Contract(
            id=r[0],
            tenant_id=r[1],
            contract_no=r[2],
            title=r[3],
            contract_type=r[4],
            party_a=r[5],
            party_b=r[6],
            supplier_id=r[7],
            sourcing_id=r[8],
            amount=r[9],
            currency=r[10],
            sign_date=r[11],
            start_date=r[12],
            end_date=r[13],
            payment_terms=r[14],
            status=r[15],
            file_url=r[16],
            signed_by=r[17],
            created_at=r[18],
            updated_at=r[19],
        )
