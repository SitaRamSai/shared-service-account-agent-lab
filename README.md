# shared-service-account-agent-lab

**Question:** a user is read-only, so an agent acting for them cannot write — true or false?

**Answer:** false. When the agent tool calls the backend with one shared, write-capable service account, the backend never sees the user. The write succeeds. Adding a single authorization check on the *user's* own permission makes the same write fail.

```
3. BEFORE authZ check: write SUCCEEDED -> T-101
   Credential the backend accepted: svc-agent-tools (not alice)
5. AFTER authZ check:  write FAILED   -> user alice is reader, write denied
```

## Run

```bash
python3 demo.py
```

No dependencies beyond Python 3.8+. All identities are fake placeholders; there is no
backend, no network and no real credential.

Other cases in the same lab: `kill_switch.py` (shared credential vs per-agent identity),
`revoke_after_queue.py` (time-of-check vs time-of-use).

## Why it matters

The MCP spec forbids passing the client's token upstream ("token passthrough"), so
upstream calls use a separate token. If that token is one shared service account, every
user inherits its scopes unless the tool enforces per-user authorization.

Takeaway: trace each action to the identity the backend actually accepted. Reporting
"user is read-only" without that trace is false assurance.

## What this is not

A design gap, not a vulnerability. Per-server static headers and a shared upstream token
are documented platform behavior. What the demo adds is the measurement that the identity
the backend accepts is the tool's, not the user's.

Setup, versions and both runs: [scorecard.md](scorecard.md).
Clip and raw run logs: [assets/](assets/).

Episode 1 of an AI-security explainer series. Source lab:
[SitaRamSai/agent-shared-credential-demo](https://github.com/SitaRamSai/agent-shared-credential-demo).
