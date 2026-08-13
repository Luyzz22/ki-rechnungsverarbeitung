"""Request-scoped authenticated audit identity.

The modular production API authenticates a concrete user or service identity before
executing tenant-scoped mutations.  Audit metadata must derive from that trusted
identity rather than client-provided actor/upload headers.
"""
from __future__ import annotations

from contextvars import ContextVar, Token


_authenticated_actor: ContextVar[str | None] = ContextVar(
    "flowcheck_authenticated_audit_actor",
    default=None,
)


class AuditIdentityError(RuntimeError):
    """Raised when a trusted audit identity cannot be established."""


def bind_authenticated_actor(actor: str) -> Token[str | None]:
    """Bind a non-empty authenticated actor to the current request context."""
    normalized = str(actor or "").strip()
    if not normalized:
        raise AuditIdentityError("AUTHENTICATED_AUDIT_ACTOR_REQUIRED")
    return _authenticated_actor.set(normalized)


def get_authenticated_actor() -> str | None:
    """Return the current trusted actor, if the request established one."""
    return _authenticated_actor.get()


def require_authenticated_actor() -> str:
    """Return the current trusted actor or fail closed."""
    actor = get_authenticated_actor()
    if not actor:
        raise AuditIdentityError("AUTHENTICATED_AUDIT_ACTOR_REQUIRED")
    return actor


def reset_authenticated_actor(token: Token[str | None]) -> None:
    """Restore a previous audit identity context (primarily for tests/workers)."""
    _authenticated_actor.reset(token)


def is_technical_actor(actor: str | None) -> bool:
    """Technical actors remain explicit and separate from human/service identity."""
    normalized = str(actor or "").strip().lower()
    return normalized.startswith(("ai:", "system:", "validator:"))


def canonical_audit_actor(candidate: str | None = None) -> str | None:
    """Use trusted request identity unless the candidate is an explicit technical actor."""
    if is_technical_actor(candidate):
        return str(candidate).strip()
    return get_authenticated_actor() or (str(candidate).strip() if candidate else None)
