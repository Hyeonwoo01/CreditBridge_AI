"""학칙 정책 규칙 (policy_rules)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import PolicyRule


def of_institution(session: Session, institution_id: int) -> list[PolicyRule]:
    stmt = select(PolicyRule).where(PolicyRule.institution_id == institution_id)
    return list(session.scalars(stmt.order_by(PolicyRule.rule_type, PolicyRule.effective_from.desc(), PolicyRule.id)))


def get(session: Session, rule_id: int) -> PolicyRule | None:
    return session.get(PolicyRule, rule_id)


def add(session: Session, rule: PolicyRule) -> PolicyRule:
    session.add(rule)
    session.flush()
    return rule
