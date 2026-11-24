#!/usr/bin/env python3
"""Revoke-after-queue: where does the role check live, and when?

Alice is admin when a write is queued. Her role is revoked to reader
before the queued write executes. Three policies:

  (a) no user check — backend only sees shared svc-agent-tools
  (b) role checked only at enqueue — stale allow rides through
  (c) role checked again at execute — against current role state

Local experiment only. No new dependencies. Same style as demo.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCredential:
    name: str
    can_write: bool


SHARED_TOOL_CRED = ToolCredential(name="svc-agent-tools", can_write=True)


class RoleStore:
    """Mutable source of truth for user roles (simulates IdP / user directory)."""

    def __init__(self) -> None:
        self._roles: dict[str, str] = {}

    def set(self, name: str, role: str) -> None:
        self._roles[name] = role

    def get(self, name: str) -> str:
        return self._roles[name]


@dataclass
class QueuedWrite:
    user: str
    title: str
    role_at_enqueue: str


class TicketBackend:
    """Downstream system. Trusts only the calling credential."""

    def __init__(self) -> None:
        self.tickets: list[str] = ["T-100 open"]

    def create_ticket(self, cred: ToolCredential, title: str) -> str:
        if not cred.can_write:
            raise PermissionError(
                f"backend rejected {cred.name}: write not permitted"
            )
        ticket_id = f"T-{100 + len(self.tickets)}"
        self.tickets.append(f"{ticket_id} {title}")
        return ticket_id


def enqueue(roles: RoleStore, user: str, title: str) -> QueuedWrite:
    role = roles.get(user)
    print(f"   enqueue: user={user} role_at_enqueue={role} title={title!r}")
    return QueuedWrite(user=user, title=title, role_at_enqueue=role)


def execute_a(backend: TicketBackend, item: QueuedWrite) -> str:
    """(a) No user check. Shared credential only."""
    return backend.create_ticket(SHARED_TOOL_CRED, item.title)


def execute_b(backend: TicketBackend, item: QueuedWrite) -> str:
    """(b) Role checked only at enqueue. Stale allow is trusted at execute."""
    if item.role_at_enqueue != "admin":
        raise PermissionError(
            f"authZ at enqueue: user {item.user} was {item.role_at_enqueue}, write denied"
        )
    return backend.create_ticket(SHARED_TOOL_CRED, item.title)


def execute_c(
    backend: TicketBackend, roles: RoleStore, item: QueuedWrite
) -> str:
    """(c) Role checked again at execute against current role state."""
    current = roles.get(item.user)
    if current != "admin":
        raise PermissionError(
            f"authZ at execute: user {item.user} is {current}, write denied"
        )
    return backend.create_ticket(SHARED_TOOL_CRED, item.title)


def run_variant(label: str, policy: str) -> None:
    print(f"=== Variant {label}: {policy} ===\n")

    roles = RoleStore()
    roles.set("alice", "admin")
    backend = TicketBackend()

    print("1. Alice role=admin (can write)")
    item = enqueue(roles, "alice", "delete all invoices")
    print()

    roles.set("alice", "reader")
    print(f"2. REVOKED: alice role now={roles.get('alice')}")
    print("3. Execute queued write\n")

    try:
        if label == "a":
            ticket_id = execute_a(backend, item)
        elif label == "b":
            ticket_id = execute_b(backend, item)
        elif label == "c":
            ticket_id = execute_c(backend, roles, item)
        else:
            raise ValueError(label)
        print(f"4. RESULT: write SUCCEEDED -> {ticket_id}")
        print(f"   Credential the backend accepted: {SHARED_TOOL_CRED.name}")
        print(f"   Tickets now: {backend.tickets}")
    except PermissionError as exc:
        print(f"4. RESULT: write FAILED -> {exc}")
        print(f"   Tickets unchanged: {backend.tickets}")
    print()


def run() -> None:
    print("=== Revoke-after-queue experiment ===\n")
    print("Setup: alice is admin at enqueue, revoked to reader before execute.")
    print("Question: is the role checked only at enqueue, or again at execute?\n")
    print(
        "Note: original demo.py authZ lives in the AgentTool wrapper,"
        " not in TicketBackend.\n"
    )

    run_variant("a", "no user check (shared credential only)")
    run_variant("b", "role checked only at enqueue")
    run_variant("c", "role checked again at execute (current role state)")

    print("Takeaway:")
    print("  (a) revoke is invisible — shared cred still writes.")
    print("  (b) stale enqueue allow rides through after revoke.")
    print("  (c) re-check at execute denies the revoked write.")
    print("Check role when the write executes, not only when it is queued.")


if __name__ == "__main__":
    run()
