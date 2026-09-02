# Arch Studio in `/dev-loop` (Cursor)

Use this when `arch_studio.json` in the run dir has `"enabled": true`. The conductor writes that manifest on `dev-loop start`. Spec acceptance (`SPEC_APPROVED`) stays separate; architecture review uses `ARCH_APPROVED`.

## Flow (after `spec.md` exists)

1. Load `arch-studio` and build from the spec + repo evidence:
   - Canonical model: `{run}/architecture/{KEY-lower}.arch.json` (or a sensible slug)
   - Output dir: `{run}/architecture/`
   - From the installed skill root:

```bash
python3 "$SKILL_ROOT/scripts/arch_studio.py" validate "{run}/architecture/*.arch.json"
python3 "$SKILL_ROOT/scripts/arch_studio.py" build "{run}/architecture/*.arch.json" --out "{run}/architecture" --strict
```

2. Open the review surface in Cursor (Glass panel):

   - Call `cursor-app-control` `open_resource` with `uri: file://{run}/architecture/review.html`
   - Summarize in chat: system boundary, critical components, top risks, blocking findings, open questions

3. In-chat gate with **AskQuestion** (recommended first):

   | Option | Action |
   | ------ | ------ |
   | Approve architecture (Recommended) | `dev-loop arch approve KEY` |
   | Request changes | `dev-loop arch reject KEY --note "…"` then revise the canonical JSON and rebuild |
   | Skip architecture review | Only when `arch_studio.json` has `"require_review": false` |

4. When architecture is approved (or not required), run the normal **spec** AskQuestion, then:

```bash
dev-loop approve KEY
```

`dev-loop approve` refuses while `require_review` is true and `ARCH_APPROVED` is missing.

## Status

```bash
dev-loop arch status KEY
dev-loop arch status KEY --format json
```

## Cursor vs Claude bridge

- **Cursor `/dev-loop`:** review happens in this Agent chat + `open_resource`. Do not require `--claude-bridge` on `arch_studio.py serve`.
- **Optional offline server:** `python3 scripts/arch_studio.py serve …` still works for persisted browser decisions; the dev-loop gate is the CLI + AskQuestion path above.

## Do not

- Treat `review.html` acceptance as `SPEC_APPROVED` or ticket-done.
- Hand-edit generated `.drawio`, HTML, or reports — change the canonical `.arch.json` and rebuild.
- Skip the architecture gate when `require_review` is true.
