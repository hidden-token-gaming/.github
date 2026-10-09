# .github

Organization-wide defaults for **Hidden Token Gaming**.

| Path | Purpose |
|---|---|
| `profile/README.md` | The organization's GitHub landing page |
| `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md` | Default community-health files for every repository |
| `.github/ISSUE_TEMPLATE/` | Issue forms per issue type: Epic, Feature, Task, Spike, Bug |
| `.github/PULL_REQUEST_TEMPLATE.md` | Default PR template |
| `.github/workflows/pr-title.yml` | Reusable check: Conventional-Commit PR title with a lower-case subject |
| `.github/workflows/changelog.yml` | Reusable check: CHANGELOG entry under `[Unreleased]`, or the `no-changelog` label |

GitHub applies the profile, the default health files and the issue forms **only while this
repository is public**. The reusable workflows work either way, because org repositories are allowed
to call them (Settings → Actions → Access).

Use the checks from another repository:

```yaml
on:
  pull_request:
    types: [opened, edited, synchronize, reopened, labeled, unlabeled]
jobs:
  title:
    uses: hidden-token-gaming/.github/.github/workflows/pr-title.yml@main
  changelog:
    uses: hidden-token-gaming/.github/.github/workflows/changelog.yml@main
```

