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

- **Phase is *when*:** a milestone per phase, matching the
  [plan](https://github.com/hidden-token-gaming/handbook/blob/main/docs/plan.md) (in the private
  handbook, staff only). Two tracks run in parallel, and each milestone's description is its exit
  gate (a condition to observe, never a date):
  - the **community track**, `L0 — Launch-ready` to `L3 — Discoverable`, gated on members and
    activity;
  - the **platform track**, `P0 — Foundations` to `P7 — Next games`, cut per game since the
    2026-10-08 review (D21): `P1 — Hub`, `P2 — War Dogs complete`, `P3 — Hub hosted` (at `L1`),
    `P4 — Counter-Strike 2` (node spend on proven demand), `P5 — Sea of Thieves, Star Citizen and
    PUBG`, `P6 — Supporters + recognition`, `P7 — Next games`. Code no longer waits for `L1`
    (D18); only community spend does. gravel-project/gravel's issues carry the same milestone
    names and sit on the board too.

  Assign every issue its phase at triage. Unscheduled work gets `backlog`.
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
- **Order:** a number, set for every open item on 2026-10-08. Epics sit at multiples of 100 in
  roadmap order (`P1` 100, `P2` 200, `L1` 300, `L0` 400, `P3` 500, `P4` 600, `L2` 700, `P5` 800,
  `P6` 900, `L3` 1000, `P7` 1100), and each epic's work items follow it in dependency order
  (`101`, `102`, …). A new item takes the next free number under its epic.
- **Start Date** and **Target Date**.

### Runbook: what only the UI can do

The API can't create board views or the auto-add workflow, so `project-sync.sh` only validates
the fields. Set these in the board's UI (**…** menu → **Workflows**, and the view tabs):

- **Views.** Today there is only **Open Issues** (table). Add:
  - **Roadmap:** timeline layout, using Start Date and Target Date, grouped by Milestone;
  - **Board:** board layout, columns by Status.
- **Auto-add to project** is done by Actions instead (below), so the board's own auto-add
  workflow stays unset. The built-in workflows already on are: item added → Todo, item closed and
  PR merged → Done, auto-close, and auto-add sub-issues.

### Board automation: `add-to-project`

Every repo (and gravel-project/gravel) calls the reusable
[`add-to-project.yml`](../.github/workflows/add-to-project.yml) on `issues: opened, reopened` and
`pull_request: opened, reopened`, which adds the item to the board with `actions/add-to-project`.
It needs **`PROJECT_ADMIN_TOKEN`**, the same secret `project-sync.sh` uses in CI:

- a classic personal access token with `repo`, `project` and `read:org`, named for the board,
  one-year expiry (fine-grained tokens are owned by one org and can't reach gravel-project);
- stored as a **repository secret in every repo**: the six here and `gravel-project/gravel`. Not
  an organization secret: both orgs are on GitHub Free, where organization-level secrets are not
  accessible by private repositories (GitHub's docs), and four of the six repos are private. The
  token value lives on the admin workstation at `~/.config/htg/project-admin-token` (mode 600,
  never in a repo), and the secrets are set from it without the value ever reaching a terminal:

  ```bash
  for r in hidden-token-gaming/{.github,handbook,site,htg,deploy,wardogs-server} gravel-project/gravel; do
    gh secret set PROJECT_ADMIN_TOKEN -R "$r" < ~/.config/htg/project-admin-token
  done
  ```

- passed to the reusable workflow with `secrets: inherit` from this org's repos, but **explicitly**
  (`secrets: {PROJECT_ADMIN_TOKEN: ${{ secrets.PROJECT_ADMIN_TOKEN }}}`) from `gravel-project/gravel`:
  inherited secrets do not reach a reusable workflow in another organization (verified 2026-10-08);
- when it is missing, the job logs a notice and skips, so Dependabot and fork PRs (which get no
  secrets) and a repo without the secret stay green. Verify after setting it: rerun a
  `project-add` run or open a test issue, and check the board.

Set in all seven repos on 2026-10-08; every caller verified on the board the same day. **The token
expires on 2027-10-07.** Rotate before then: make a new token, update the file on the admin workstation,
run the loop above, and change this date.

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

## Repository settings

These are set by hand, because `project-sync.sh` covers labels, milestones, issue types and the
board, not security settings. Re-check them with the commands below after any change.

**Org:**

- Two-factor authentication is required for every member and outside collaborator. GitHub only
  lets you turn this on in the UI (org Settings → Authentication security). The API can read it
  but not set it.
- Members can't create repositories, public or private. Owners create them.
- Base permission is read.

**Every repo:** squash merge only, the squash commit takes the PR title, and head branches are
deleted on merge. That's why the `pr-title` check is what lands on `main`.

**Public repos (`.github`, `site`):** each has a branch ruleset named `main` on the default
branch. The desired state is in [`.github/rulesets/`](../.github/rulesets/), one file per repo:

- a pull request is required, squash only, with no approvals (one maintainer for now);
- linear history and signed commits are required (GitHub signs squash merges made on the site);
- force-pushes and deleting `main` are blocked;
- these checks must pass: `title / title`, `changelog / changelog` and `label / label`. `site`
  also requires `build` and `markdown`. Its preview `deploy` job isn't required, because a
  Cloudflare problem shouldn't block a merge, and it doesn't run for forks or Dependabot.
- There are no bypass actors, so owners also go through a PR.

A job that's skipped, such as `label` on a fork or Dependabot PR, still passes the check.

Free-plan private repos can't enforce rulesets, so in `handbook`, `htg`, `deploy` and
`wardogs-server` squash-only merging and these checks rely on discipline.

```bash
# apply (create once; afterwards PUT to .../rulesets/<id> with the same file)
gh api -X POST repos/hidden-token-gaming/site/rulesets --input .github/rulesets/site.json
# verify
gh api orgs/hidden-token-gaming --jq '{two_factor_requirement_enabled, members_can_create_repositories}'
gh api repos/hidden-token-gaming/site/rules/branches/main --jq '.[].type'
```

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
