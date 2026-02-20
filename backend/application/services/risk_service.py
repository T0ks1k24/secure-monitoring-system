from domain.enums.risk_enum import RiskLevel


class RiskService:

    def evaluate(self, persons: int, zone_limit: int) -> RiskLevel:

        if persons <= zone_limit:
            return RiskLevel.LOW

        if persons <= zone_limit * 1.5:
            return RiskLevel.MEDIUM

        return RiskLevel.HIGH
