from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Staff, Role


class StaffRepository(BaseRepository[Staff]):
    """员工数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'staff'

    def _from_row(self, row) -> Staff:
        return Staff.from_row(row)

    # ---- 写 ----

    def add(self, staff: Staff) -> Staff:
        cur = self._db.execute(
            '''INSERT INTO staff
               (tenant_id,mall_id,user_id,name,employee_no,position,phone,status,hired_at)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (staff.tenant_id, staff.mall_id, staff.user_id, staff.name,
             staff.employee_no, staff.position, staff.phone, staff.status, staff.hired_at),
        )
        self._db.commit()
        staff.id = cur.lastrowid
        return staff

    def update(self, staff: Staff) -> bool:
        cur = self._db.execute(
            '''UPDATE staff SET name=?,position=?,phone=?,mall_id=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (staff.name, staff.position, staff.phone, staff.mall_id, staff.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_status(self, staff_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE staff SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, staff_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 读 ----

    def find_by_tenant(self, tenant_id: int) -> List[Staff]:
        return self._fetchall('SELECT * FROM staff WHERE tenant_id=? ORDER BY id', (tenant_id,))

    def find_by_mall(self, mall_id: int) -> List[Staff]:
        return self._fetchall('SELECT * FROM staff WHERE mall_id=? ORDER BY id', (mall_id,))

    def find_by_employee_no(self, tenant_id: int, employee_no: str) -> Optional[Staff]:
        return self._fetchone(
            'SELECT * FROM staff WHERE tenant_id=? AND employee_no=?',
            (tenant_id, employee_no),
        )

    # ---- 角色分配 ----

    def assign_role(self, staff_id: int, role_id: int) -> bool:
        try:
            self._db.execute(
                'INSERT OR IGNORE INTO staff_roles (staff_id,role_id) VALUES (?,?)',
                (staff_id, role_id),
            )
            self._db.commit()
            return True
        except Exception:
            self._db.rollback()
            return False

    def revoke_role(self, staff_id: int, role_id: int) -> bool:
        cur = self._db.execute(
            'DELETE FROM staff_roles WHERE staff_id=? AND role_id=?', (staff_id, role_id))
        self._db.commit()
        return cur.rowcount > 0

    def get_roles(self, staff_id: int) -> List[Role]:
        rows = self._db.execute(
            '''SELECT r.* FROM roles r
               JOIN staff_roles sr ON sr.role_id=r.id
               WHERE sr.staff_id=? ORDER BY r.name''',
            (staff_id,),
        ).fetchall()
        return [Role.from_row(r) for r in rows]

    def has_permission(self, staff_id: int, permission_code: str) -> bool:
        n = self._db.execute(
            '''SELECT COUNT(*) FROM staff_roles sr
               JOIN role_permissions rp ON rp.role_id=sr.role_id
               JOIN permissions p ON p.id=rp.permission_id
               WHERE sr.staff_id=? AND p.code=?''',
            (staff_id, permission_code),
        ).fetchone()[0]
        return n > 0
