"""Decision priority levels."""

from enum import IntEnum


class Priority(IntEnum):
    """Priority levels for decisions.

    Higher values indicate higher urgency.
    """
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        mapping = {
            "low": cls.LOW,
            "normal": cls.NORMAL,
            "high": cls.HIGH,
            "critical": cls.CRITICAL,
            "emergency": cls.EMERGENCY,
        }
        return mapping.get(value.lower(), cls.NORMAL)
