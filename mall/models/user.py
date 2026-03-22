from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """用户模型"""
    username: str
    password: str
    email: str
    phone: str = ''
    address: str = ''
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
        }

    @staticmethod
    def from_row(row: tuple) -> 'User':
        user = User(
            id=row[0],
            username=row[1],
            password=row[2],
            email=row[3],
            phone=row[4] or '',
            address=row[5] or '',
        )
        user.created_at = row[6]
        user.updated_at = row[7]
        return user
