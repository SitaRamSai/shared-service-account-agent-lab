# agent-shared-credential-demo

A read-only user can write through an AI agent tool when the tool calls the backend with one shared, write-capable service account. The backend only ever sees the service account, never the user.

This demo shows the write **succeeding** under the shared credential, then **failing** once the tool adds a single authZ check on the *user's* own permission.

## Run

```bash
python3 demo.py
```

No dependencies (Python 3.8+). All identities are fake placeholders.

## Why it matters

The MCP spec forbids passing the client's token upstream ("token passthrough"), so upstream calls use a separate token. If that token is one shared service account, every user inherits its scopes unless the tool enforces per-user authorization:
https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations

Takeaway: trace each action to the identity the backend actually accepted.

## More demos

### Kill switch: shared credential vs per-agent identity

```bash
python3 kill_switch.py
```

Three agents (support, billing, research), one compromised.

- **Shared service account:** revoking the user does nothing, and revoking the shared credential stops all three agents.
- **One credential per agent:** revoking only `research-agent` stops it while support and billing keep writing.

A kill switch only works if each agent has its own credential.

### Revoked after queueing (time-of-check vs time-of-use)

```bash
python3 revoke_after_queue.py
```

Alice queues a write as `admin`, then is downgraded to `reader` before it runs.

- (a) No user check: the write **succeeds**.
- (b) Role checked only at enqueue: the write **succeeds** (stale allow).
- (c) Role re-checked at execute: the write is **denied**.

Check the role when the write executes, not only when it is queued.
