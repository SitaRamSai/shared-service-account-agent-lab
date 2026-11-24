# Scorecard — episode 1

## Setup

- Source lab: `SitaRamSai/agent-shared-credential-demo`, adapted unchanged in behavior.
- One synthetic user `alice` (`role=reader`) and one shared tool credential
  `svc-agent-tools` (`can_write=True`). No backend, no network, no real accounts.
- Command: `python3 demo.py`

## Versions

| | |
| --- | --- |
| Date | 2026-11-23 |
| Python | 3.9.6 |
| Dependencies | none (standard library only) |

## Runs

Two consecutive runs on 2026-11-23, outputs committed as `assets/run1.log` and
`assets/run2.log`. Both runs produced identical output:

- Before the authZ check: write **succeeded**, backend accepted `svc-agent-tools`.
- After adding `user.role == admin`: the same write **failed**.
- Result count: 2 of 2 runs reproduced; no run differed.

## Negative case

The check that fails is the point: with it removed, the write succeeds every time. The
demo also ships `kill_switch.py` and `revoke_after_queue.py` as adjacent cases.

## What this does not show

- No real service, token exchange or MCP server is involved; the credential boundary is
  simulated in one file.
- It does not measure what a live model would choose, nor any real application's policy.
- Design gap, not a vulnerability: per-server static headers and a shared upstream token
  are documented platform behavior.

## Reproduce

```bash
python3 demo.py
```
