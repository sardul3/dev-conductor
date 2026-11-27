# Product-guide

Date: 2026-11-26
Status: design, not implemented
Repo: `dev-conductor`

## Goal

A product-owner interview that sits in front of the build loop. It talks to stakeholders in product language, writes the product pack, and files one Jira epic plus ordered child stories. `/dev-loop KEY` is unchanged and still writes the technical spec later, one child at a time.

The interview does not discuss architecture, stack, APIs, schemas, data models, file layout, or code.

## Approaches considered

1. **Skill plus a file command.** The agent runs the interview. Python only checks the pack and creates the Jira issues. Recommended, and this is the design below.
2. **A fixed question form in the CLI.** Weaker. A champion product owner follows the answers, and a form cannot.
3. **Folding the interview into `story-spec`.** Rejected. That skill locks technical seams, and it runs after a ticket already exists.

## Interview

New skill: `skills/product-guide/SKILL.md`. Source of truth is `skills/`. The plugin and install already publish that tree.

The agent is the product owner. The person is the stakeholder. Reuse the grill rhythm from `design-tree-interview`: each round asks the whole frontier, numbers each question, gives a recommended answer, then waits. Do not reuse that skill's codebase lookup. Do not read the repo. Do not launch prompt-enrich.

Frontier, in dependency order. A later round waits on the earlier one.

1. Who hurts, what happens today, and the idea in their words.
2. The outcome: what is true for them when this is done. Who it is for, and who it is not for.
3. How we will know it worked. One success measure a stakeholder can check without reading a diff.
4. Scope: now, next, and never.
5. Priority order, deadlines, and what slips if a date is fixed.
6. Risks, assumptions, and decisions that depend on another team or another stakeholder. Business dependencies only.
7. Release slices. Each slice is one outcome a person can use. The first slice is the smallest one that proves the outcome.

When the frontier is empty, restate the pack in plain language and ask for acceptance. On yes, write `PRODUCT_APPROVED` containing their name. Do not file Jira from the skill. Tell them to run `product-file`. Do not start `/dev-loop`. Do not write application code.

If they describe a solution in technical terms, restate it as a user outcome and ask whether that outcome is the one they want.

## Product pack

One run directory, `~/.config/dev-conductor/dev-loop/runs/product-<slug>/`. `<slug>` is a short hyphenated name taken from the outcome. These files:

| File | Holds |
| --- | --- |
| `problem.md` | Who hurts. What happens today. The idea in their words. |
| `prd.md` | A level-1 title, then problem, users, non-users, outcome, success measure, now, next, never, risks, assumptions. |
| `plan.md` | Ordered slices, deadlines, the first slice, and business dependencies. |
| `decisions.md` | Each decision, the recommended answer, and what they chose. |
| `stories.md` | One section per slice, in priority order. |
| `PRODUCT_APPROVED` | The stakeholder's name. Absent until they accept. |

`prd.md` starts with one level-1 heading. That heading is the epic summary. It then uses these level-2 headings, each with at least one sentence under it: `Problem`, `Users`, `Non-users`, `Outcome`, `Success`, `Now`, `Next`, `Never`, `Risks`, `Assumptions`.

`stories.md` is the only file the filer parses for children. One story looks like this:

```markdown
## 1. Invite a teammate

Priority: must
Deadline: 2026-12-01
Outcome: An owner can give a teammate access without sending a password.
Acceptance:
- The owner names the teammate and the teammate can get in.
- The owner can take that access away.
Out of scope:
- Billing for extra seats.
```

`Priority` is `must`, `should`, or `later`. `Deadline` is `YYYY-MM-DD` or `none`. Rank is the integer in the heading. Ranks start at 1 and increase by one with no gaps.

## Filing

`python3 dev-loop/cli.py product-file --run <dir>`

Refuse, exit non-zero, and create nothing when any of these is true:

- `PRODUCT_APPROVED` is missing or blank.
- A required `prd.md` heading is missing or empty.
- `stories.md` has no stories, a broken rank sequence, a bad priority, or a bad deadline.
- Any pack file contains a fenced code block, a path whose final suffix is `.py`, `.ts`, `.tsx`, `.js`, `.java`, or `.go`, or a heading named `Architecture`, `Implementation`, `Schema`, `Data model`, or `Tech stack`.

On success, in this order:

1. Create one Epic in the configured Jira project. Summary is the level-1 heading of `prd.md`. Description is the problem, the PRD, the plan, and the decisions, as plain paragraphs. Label: `product-guide`.
2. Create one Story per slice, rank order. Summary is `N. <title>`. Description is outcome, acceptance, out of scope, priority, and deadline. `parent` is the epic key. Same label.
3. Write `jira.json` in the run dir: `epic` key, then `stories` as `{rank, key, summary}`.

Use `jira_request` in `dev-loop/jira_client.py`. `POST /rest/api/3/issue`. Description is Atlassian document format: one paragraph per blank-line block. Issue type names come from config, default `Epic` and `Story`.

If a child create fails after the epic exists, write `jira.json` with the epic and any children already created, print the epic key and the error, and stop. Do not delete the epic. Do not create the remaining children. Exit non-zero.

`product-file` does not fetch, grill, or start `/dev-loop`.

Config, under `product` in `dev-loop/config.yaml.example`:

```yaml
product:
  epic_type: Epic
  story_type: Story
  label: product-guide
```

Project, site, and credentials stay the existing `jira` block and `secrets.env`. Nothing new is committed.

## How the build loop picks it up

No change to `start` or `continue`. A child story is an ordinary issue. `fetch_issue` already returns summary and description, and `story-spec` still writes the technical `spec.md` for that key.

The epic is the product record. The skill tells the stakeholder to run `/dev-loop` on a child key from `jira.json`, not on the epic. This change does not detect an epic and refuse it.

## Tests

Failing tests first, in `dev-loop/tests/test_product_guide.py`, with a fake `urlopen` and no network.

- Missing or blank `PRODUCT_APPROVED` creates nothing.
- A missing PRD heading creates nothing.
- A fenced code block creates nothing.
- A source path creates nothing.
- A forbidden heading creates nothing.
- A valid pack creates the epic first, then each story with that parent key, in rank order, and writes `jira.json`.
- A failed second story leaves `jira.json` containing the epic and the first story, and does not attempt the third.

## Out of this change

Technical spec, plan internals, architecture notes, starting `/dev-loop`, editing tickets this run did not create, poller, auto-merge, and deploy.
