from enum import Enum


class RiskLevel(str, Enum):

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_value(cls, value: str) -> "RiskLevel":
        return cls(value.upper())
