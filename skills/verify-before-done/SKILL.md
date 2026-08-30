---
name: verify-before-done
description: Use before claiming work is complete, fixed, or passing, and before commit or PR. Run the proof command in this turn.
---

# Verify before done

**Iron law:** no success claim without fresh evidence from this turn.

| Claim | Proof |
| ----- | ----- |
| Tests pass | Test command, 0 failures, exit 0 |
| Bug fixed | The original failing case now passes |
| Build works | Build command exit 0 |
| Lint clean | Linter output, 0 errors |

Not proof: previous run, “should work”, agent said success, linter ≠ tests.

State the command, run it, read the output, then claim. If it failed, say it failed.
