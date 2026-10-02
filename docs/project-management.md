# Project management

How work across the `hidden-token-gaming` repos is planned, tracked and prioritised. It follows
the GitHub-native **pm-framework** v1.0, org edition, from
[mkzsystems/pm-framework](https://github.com/mkzsystems/pm-framework), with one deviation:
a **single org-level spec covers every repo** (below).

The desired state lives in [`.github/project.yml`](../.github/project.yml):

- labels and phase milestones for every repo;
- the org's issue types;
- the board's fields.

[`scripts/project-sync.sh`](../scripts/project-sync.sh) reconciles it, non-destructively.

## Deviation: one spec for many repos

The framework's `project.yml` describes one repo. HTG's work spans several (`handbook`, `htg`,
`deploy`, `site`, `wardogs-server`, `.github`) and runs on one board with one set of phases, so
one spec lists them all:

- **Shared labels** (triage, games, GitHub's defaults) and the **P0–P6 milestones** go to every
  repo.
- **Each repo's own `component:*` labels** come from its entry under `repos:`.
- **Issue types and board fields** are org-level and validated once.

A new repo is added under `repos:` with its components, then synced.

## Two axes: phase × epic

- **Phase is *when*:** a milestone per phase, `P0 — Foundations` to `P6 — Next games`, matching
  the [plan](https://github.com/hidden-token-gaming/handbook/blob/main/docs/plan.md) (in the
  private handbook, staff only). Assign every issue its phase at triage. Unscheduled work gets
  `backlog`.
- **Epic is *which initiative*:** an Epic issue with native sub-issues, which can live in any repo.
  The board's *Sub-issues progress* rolls them up. An epic carries the milestone of the phase it
  finishes in.

## Kind of work

Every issue gets exactly one **issue type**: Epic, Feature, Task, Spike or Bug. The issue forms
in this repo set it. There are no `type:*` labels.

## Labels

- **`component:*`:** the subsystem a change touches, mirroring the Conventional-Commit scope.
  Each repo's `.github/labeler.yml` applies them to PRs by path.
- **`game:*`:** which game an issue concerns (`sot`, `sc`, `wardogs`, `cs2`, `pubg`, `more`).
- **Triage and workflow:** `needs-triage`, `backlog`, `blocked`, `architecture`, `no-changelog`
  (exempts a PR from the CHANGELOG check).
- **GitHub's defaults** (`bug`, `documentation`, …) are kept consistent across repos.

There are no phase labels (milestones are the phases) and no priority labels (the Order field
ranks work).

## The board

[HTG Platform](https://github.com/orgs/hidden-token-gaming/projects/1). Fields:

- **Status:** Todo / In Progress / Done.
- **Effort:** High / Medium / Low, set at filing.
- **Order:** a number. Epics are `1–N`, and work items sit in per-phase thousand-bands.
- **Start Date** and **Target Date**.

### Runbook: what only the UI can do

The API can't create board views or the auto-add workflow, so `project-sync.sh` only validates
the fields. Set these in the board's UI (**…** menu → **Workflows**, and the view tabs):

- **Views.** Today there is only **Open Issues** (table). Add:
  - **Roadmap:** timeline layout, using Start Date and Target Date, grouped by Milestone;
  - **Board:** board layout, columns by Status.
- **Auto-add to project.** Add one workflow per repo with the filter `is:issue,pr is:open`.
  On GitHub's Free plan a project may be limited in how many auto-add workflows it has. If so,
  add the busiest repos first and add the rest at triage. The built-in workflows already on are:
  item added → Todo, item closed and PR merged → Done, auto-close, and auto-add sub-issues.

## Triage checklist

- [ ] **Issue type** set
- [ ] **Milestone**, or `backlog`
- [ ] **`component:*`** and **`game:*`** labels
- [ ] **Parent epic** linked as a sub-issue
- [ ] **On the board** with Status `Todo`
- [ ] **Effort** set

## Delivery loop

1. Branch off `main` (`<type>/<kebab>`), one issue per branch.
2. Conventional Commits; the scope is the component.
3. PR title in Conventional-Commit form with a lowercase subject, enforced by the reusable
   `pr-title` check. The body says `Closes #N`.
4. A `CHANGELOG.md` entry under `[Unreleased]`, or the `no-changelog` label, enforced by the
   reusable `changelog` check.
5. Squash-merge on green CI.

## Keeping it in sync

```bash
scripts/project-sync.sh --dry-run        # report drift: exit 0 none, 2 drift, 1 error
scripts/project-sync.sh                  # create/update what differs, then verify
scripts/project-sync.sh --dry-run --repo site
```

It needs a `gh` session with `repo` and `read:project` scopes, and `read:org` for issue types.
It creates and updates labels and milestones but never deletes them, and lists any it leaves
alone as "unmanaged". Issue types and board fields are validated only, so a difference there is
reported as drift to fix by hand. An API failure is an error (exit 1), never "no drift".
