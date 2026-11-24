#!/usr/bin/env python3
"""§19 reproducible case: read-only user + write-capable shared tool credential.

Shows why "user is read-only" is not the same as "the write was authorized."
Minimal, self-contained reproduction.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    name: str
    role: str  # "reader" | "admin"


@dataclass(frozen=True)
class ToolCredential:
    """Identity the *backend* actually accepts for this tool."""

    name: str
    can_write: bool


# Shared service account the agent tool is wired to (typical MCP/proxy pattern).
SHARED_TOOL_CRED = ToolCredential(name="svc-agent-tools", can_write=True)


class TicketBackend:
    """Downstream system. Trusts only the calling credential, not the end-user claim."""

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


class AgentTool:
    """Tool the agent calls. Forwards the shared credential, not the user token."""

    def __init__(self, backend: TicketBackend, cred: ToolCredential) -> None:
        self.backend = backend
        self.cred = cred
        self.require_user_write = False  # flipped on in step 3

    def open_ticket(self, user: User, title: str) -> str:
        if self.require_user_write and user.role != "admin":
            raise PermissionError(
                f"authZ check: user {user.name} is {user.role}, write denied"
            )
        return self.backend.create_ticket(self.cred, title)


def scenario(authz_check: bool) -> None:
    """One run of the case. `authz_check=False` is the vulnerable configuration."""
    user = User(name="alice", role="reader")  # read-only end user
    backend = TicketBackend()
    tool = AgentTool(backend, SHARED_TOOL_CRED)

    tool.require_user_write = authz_check
    state = "ON" if authz_check else "OFF"
    print(f"=== read-only user + shared write-capable tool cred (authZ check {state}) ===\n")
    print(f"1. End user: {user.name} role={user.role}")
    print(f"2. Tool credential backend will accept: {tool.cred.name} can_write={tool.cred.can_write}")
    print(
        "3. Authorization check on the user's own permission: "
        + ("user must be admin" if authz_check else "none")
    )
    print()
    try:
        ticket_id = tool.open_ticket(user, "delete all invoices")
        print(f"4. WRITE SUCCEEDED -> {ticket_id}")
        print(f"   Credential the backend accepted: {tool.cred.name} (not {user.name})")
        print("   Why allowed: backend only saw the shared write-capable tool identity.")
    except PermissionError as exc:
        print(f"4. WRITE FAILED -> {exc}")
        print("   Same user, same tool, same shared cred. The check changed the outcome.")
    print()


def run() -> None:
    user = User(name="alice", role="reader")  # read-only end user
    backend = TicketBackend()
    tool = AgentTool(backend, SHARED_TOOL_CRED)

    print("=== §19 case: read-only user + write-capable shared tool cred ===\n")
    print(f"1. End user: {user.name} role={user.role}")
    print(f"2. Tool credential backend will accept: {tool.cred.name} can_write={tool.cred.can_write}")
    print()

    # Step 1-2: write succeeds; identity accepted is the shared cred
    ticket_id = tool.open_ticket(user, "delete all invoices")
    print(f"3. BEFORE authZ check: write SUCCEEDED -> {ticket_id}")
    print(f"   Credential the backend accepted: {tool.cred.name} (not {user.name})")
    print(f"   Why allowed: backend only saw the shared write-capable tool identity.")
    print()

    # Step 3: add the missing authorization check (user must be able to write)
    tool.require_user_write = True
    print("4. Added missing check: tool requires user.role == admin before calling backend")
    print()

    # Step 4: same request now fails
    try:
        tool.open_ticket(user, "delete all invoices again")
        print("5. AFTER authZ check: unexpected success")
    except PermissionError as exc:
        print(f"5. AFTER authZ check: write FAILED -> {exc}")
        print("   Same user, same tool, same shared cred. The check changed the outcome.")
    print()
    print("Takeaway: follow one action to the identity the backend accepted.")
    print("Reporting 'user is read-only' without that trace is false assurance.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Shared service account case (episode 1).")
    parser.add_argument(
        "--mode",
        choices=("full", "before", "after"),
        default="full",
        help="full = before/after narrative (default); before/after = one configuration",
    )
    args = parser.parse_args()

    if args.mode == "before":
        scenario(authz_check=False)
    elif args.mode == "after":
        scenario(authz_check=True)
    else:
        run()
