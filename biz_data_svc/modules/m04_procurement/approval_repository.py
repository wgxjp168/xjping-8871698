"""
审批流程 Repository
继承 BaseRepository[ApprovalWorkflow]，管理审批工作流、节点、实例与记录。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import ApprovalWorkflow, ApprovalNode, ApprovalInstance, ApprovalRecord


class ApprovalRepository(BaseRepository[ApprovalWorkflow]):
    """approval_workflows 表的数据访问层（兼管节点/实例/记录）"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'approval_workflows'

    def _from_row(self, row) -> ApprovalWorkflow:
        return ApprovalWorkflow.from_row(row)

    # ------------------------------------------------------------------ #
    #  工作流 CRUD                                                          #
    # ------------------------------------------------------------------ #

    def add_workflow(self, wf: ApprovalWorkflow) -> ApprovalWorkflow:
        """新增审批工作流定义"""
        cur = self._db.execute(
            '''
            INSERT INTO approval_workflows
                (tenant_id, name, business_type, status, is_default)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (wf.tenant_id, wf.name, wf.business_type, wf.status, wf.is_default),
        )
        self._db.commit()
        wf.id = cur.lastrowid
        return wf

    def find_workflow_by_type(
        self, tenant_id: int, business_type: str
    ) -> Optional[ApprovalWorkflow]:
        """按业务类型查询默认工作流"""
        return self._fetchone(
            '''
            SELECT * FROM approval_workflows
            WHERE tenant_id = ? AND business_type = ? AND is_default = 1
            ORDER BY id DESC LIMIT 1
            ''',
            (tenant_id, business_type),
        )

    # ------------------------------------------------------------------ #
    #  节点 CRUD                                                            #
    # ------------------------------------------------------------------ #

    def add_node(self, node: ApprovalNode) -> ApprovalNode:
        """新增审批节点"""
        cur = self._db.execute(
            '''
            INSERT INTO approval_nodes
                (workflow_id, node_name, node_type, approver_ids,
                 sort_order, condition_expr, action_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                node.workflow_id, node.node_name, node.node_type,
                node.approver_ids, node.sort_order,
                node.condition_expr, node.action_type,
            ),
        )
        self._db.commit()
        node.id = cur.lastrowid
        return node

    def list_nodes(self, workflow_id: int) -> List[ApprovalNode]:
        """列出工作流所有节点，按 sort_order 升序"""
        rows = self._db.execute(
            'SELECT * FROM approval_nodes WHERE workflow_id = ? ORDER BY sort_order',
            (workflow_id,),
        ).fetchall()
        return [ApprovalNode.from_row(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  审批实例                                                              #
    # ------------------------------------------------------------------ #

    def start_instance(
        self, workflow_id: int, business_type: str, business_id: int
    ) -> ApprovalInstance:
        """发起一次审批实例，current_node 从 1 开始"""
        cur = self._db.execute(
            '''
            INSERT INTO approval_instances
                (workflow_id, business_type, business_id, current_node,
                 status, started_at)
            VALUES (?, ?, ?, 1, 'pending', datetime('now'))
            ''',
            (workflow_id, business_type, business_id),
        )
        self._db.commit()
        instance_id = cur.lastrowid
        return self.find_instance_by_id(instance_id)

    def find_instance(
        self, business_type: str, business_id: int
    ) -> Optional[ApprovalInstance]:
        """按业务类型和业务ID查询审批实例"""
        row = self._db.execute(
            '''
            SELECT * FROM approval_instances
            WHERE business_type = ? AND business_id = ?
            ORDER BY id DESC LIMIT 1
            ''',
            (business_type, business_id),
        ).fetchone()
        return ApprovalInstance.from_row(row) if row else None

    def find_instance_by_id(self, id: int) -> Optional[ApprovalInstance]:  # noqa: A002
        """按主键查询审批实例"""
        row = self._db.execute(
            'SELECT * FROM approval_instances WHERE id = ?', (id,)
        ).fetchone()
        return ApprovalInstance.from_row(row) if row else None

    def advance_node(self, instance_id: int) -> bool:
        """推进审批节点：current_node += 1"""
        cur = self._db.execute(
            'UPDATE approval_instances SET current_node = current_node + 1 WHERE id = ?',
            (instance_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def complete_instance(
        self,
        instance_id: int,
        status: str,
        completed_by: Optional[int] = None,
    ) -> bool:
        """完成审批实例，设置终态状态、完成时间和操作人"""
        cur = self._db.execute(
            '''
            UPDATE approval_instances
            SET status = ?,
                completed_at = datetime('now'),
                completed_by = ?
            WHERE id = ?
            ''',
            (status, completed_by, instance_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  审批记录                                                              #
    # ------------------------------------------------------------------ #

    def record(self, rec: ApprovalRecord) -> ApprovalRecord:
        """写入一条审批操作记录"""
        cur = self._db.execute(
            '''
            INSERT INTO approval_records
                (instance_id, node_id, node_order, approver_id,
                 action, comment, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                rec.instance_id, rec.node_id, rec.node_order,
                rec.approver_id, rec.action, rec.comment, rec.attachments,
            ),
        )
        self._db.commit()
        rec.id = cur.lastrowid
        return rec

    def list_records(self, instance_id: int) -> List[ApprovalRecord]:
        """列出某审批实例的所有操作记录"""
        rows = self._db.execute(
            'SELECT * FROM approval_records WHERE instance_id = ? ORDER BY id',
            (instance_id,),
        ).fetchall()
        return [ApprovalRecord.from_row(r) for r in rows]

    def get_pending_approvals(self, approver_id: int) -> List[ApprovalInstance]:
        """获取指定审批人待处理的审批实例列表"""
        # 通过 approval_nodes 找到该审批人所在节点，再关联实例
        rows = self._db.execute(
            '''
            SELECT DISTINCT ai.*
            FROM approval_instances ai
            JOIN approval_nodes an
                ON an.workflow_id = ai.workflow_id
               AND an.sort_order = ai.current_node
            WHERE ai.status = 'pending'
              AND (
                  an.approver_ids = ?
                  OR an.approver_ids LIKE ? || ',%'
                  OR an.approver_ids LIKE '%,' || ?
                  OR an.approver_ids LIKE '%,' || ? || ',%'
              )
            ORDER BY ai.started_at
            ''',
            (
                str(approver_id),
                str(approver_id),
                str(approver_id),
                str(approver_id),
            ),
        ).fetchall()
        return [ApprovalInstance.from_row(r) for r in rows]
