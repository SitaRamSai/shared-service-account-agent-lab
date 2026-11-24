#!/usr/bin/env python3
"""Kill switch: shared credential vs per-agent identity.

Three agents call the same ticket backend. research-agent is compromised.
A kill switch revokes credentials. Two modes:

  Mode A: all agents share svc-agent-tools
    - do not revoke: the compromised agent keeps writing
    - revoke the shared credential: every agent's next call fails
  Mode B: each agent has its own credential
    - revoke only research-agent: it is denied; the others still succeed

Local experiment only. No new dependencies. Same style as demo.py.
"""

from __future__ import annotations

from dataclasses import dataclass


AGENTS = ("support-agent", "billing-agent", "research-agent")
COMPROMISED = "research-agent"
SHARED_CRED_NAME = "svc-agent-tools"


@dataclass(frozen=True)
class ToolCredential:
    """Identity the *backend* actually accepts for this tool."""

    name: str
    can_write: bool


class CredentialStore:
    """Mutable source of truth for credentials (simulates IdP revocation)."""

    def __init__(self) -> None:
        self._creds: dict[str, ToolCredential] = {}

    def issue(self, name: str, can_write: bool = True) -> None:
        self._creds[name] = ToolCredential(name=name, can_write=can_write)

    def get(self, name: str) -> ToolCredential:
        return self._creds[name]

    def revoke(self, name: str) -> None:
        current = self._creds[name]
        self._creds[name] = ToolCredential(name=current.name, can_write=False)


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


def cred_for(store: CredentialStore, agent: str, shared: bool) -> ToolCredential:
    name = SHARED_CRED_NAME if shared else f"cred-{agent}"
    return store.get(name)


def attempt(backend: TicketBackend, store: CredentialStore, agent: str, shared: bool) -> str:
    cred = cred_for(store, agent, shared)
    try:
        ticket_id = backend.create_ticket(cred, f"write from {agent}")
        return f"   {agent:<16} write SUCCEEDED -> {ticket_id}   cred={cred.name}"
    except PermissionError as exc:
        return f"   {agent:<16} write DENIED    -> {exc}"


def run_calls(backend: TicketBackend, store: CredentialStore, shared: bool) -> None:
    for agent in AGENTS:
        print(attempt(backend, store, agent, shared))


def run_mode_a() -> None:
    print("--- Mode A: all agents share svc-agent-tools ---\n")

    store = CredentialStore()
    store.issue(SHARED_CRED_NAME, can_write=True)

    print("1. Before the kill switch")
    print(f"   Shared credential: {SHARED_CRED_NAME} can_write=True")
    backend = TicketBackend()
    run_calls(backend, store, shared=True)
    print()

    print("2. Option A1: do not revoke")
    print(f"   {COMPROMISED} is still presenting {SHARED_CRED_NAME}")
    run_calls(backend, store, shared=True)
    print("   Result: the kill switch was not pulled. The compromised agent still writes.")
    print()

    print("3. Option A2: revoke the shared credential (collateral damage)")
    store.revoke(SHARED_CRED_NAME)
    cred = store.get(SHARED_CRED_NAME)
    print(f"   REVOKED: {cred.name} can_write={cred.can_write}")
    run_calls(backend, store, shared=True)
    print("   Result: the compromised agent stops, and so does the rest of the fleet.")
    print()


def run_mode_b() -> None:
    print("--- Mode B: each agent has its own credential ---\n")

    store = CredentialStore()
    for agent in AGENTS:
        store.issue(f"cred-{agent}", can_write=True)

    print("1. Before the kill switch")
    for agent in AGENTS:
        cred = store.get(f"cred-{agent}")
        print(f"   {agent}: {cred.name} can_write={cred.can_write}")
    backend = TicketBackend()
    run_calls(backend, store, shared=False)
    print()

    print(f"2. Revoke only {COMPROMISED}")
    store.revoke(f"cred-{COMPROMISED}")
    cred = store.get(f"cred-{COMPROMISED}")
    print(f"   REVOKED: {cred.name} can_write={cred.can_write}")
    run_calls(backend, store, shared=False)
    print("   Result: only the compromised agent is stopped. The others keep working.")
    print()


def run() -> None:
    print("=== Kill switch: shared credential vs per-agent identity ===\n")
    print("Setup: three agents call the same ticket backend.")
    print("       support-agent, billing-agent, research-agent (compromised)")
    print("Question: can we stop the compromised agent without taking down the fleet?\n")

    run_mode_a()
    run_mode_b()

    print("Takeaway:")
    print("  On a shared service account, the kill switch either takes down the")
    print("  fleet or does nothing. A kill switch only works if each agent has")
    print("  its own credential.")


if __name__ == "__main__":
    run()
