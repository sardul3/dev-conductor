---
name: verify-before-done
description: Run the proof command in this turn before claiming tests pass, a bug is fixed, or work is ready to commit or PR. Use whenever you are about to say done, green, or passing. In /dev-loop, the CLI owns the verify stage — still run tests before you write STAGE_DONE as the writer.
---

# Verify before done

A success claim without a command from **this turn** is a guess. Previous logs, “should work”, and another agent’s word are not proof.

| Claim | Proof from this turn |
| ----- | -------------------- |
| Tests pass | Test command, 0 failures, exit 0 |
| Bug fixed | The original failing case now passes |
| Build works | Build command exit 0 |
| Lint clean | Linter output, 0 errors |

State the command, run it, read the output, then claim. If it failed, say it failed.

## `/dev-loop`

- **Writer / test-writer / rewrite:** run the inferred test command before `STAGE_DONE`. Infer it from manifests, not from memory of another repo. After green, write terminal snapshots (`tests.png`, `run.png`, `curl.png` as applicable) to `~/.config/dev-conductor/dev-loop/runs/KEY/evidence/` before `STAGE_DONE`. Browser screenshot, macOS `screencapture`, or a PNG of the terminal. Text-only `verify.log` is not enough.
- **Verify stage:** in-process CLI writes `verify.log`. Do not skip `step` and claim verify yourself. Do not open a PR (`finish-branch` is not ship). If snapshots are still missing after verify is green, capture them **before** `step` ship — ship refuses without them when `evidence.require_visual` (default true).
- Red verify → writer retry via `step`. Debug with `systematic-debugging`; do not weaken tests except compile/syntax/simple IO or a spec contradiction.
