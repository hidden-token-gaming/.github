# Contributing

Thanks for helping build Hidden Token Gaming.

- **Start from an issue.** Every change is one issue → one branch → one pull request, squash-merged.
  Use the issue forms (Epic, Feature, Task, Spike, Bug).
- **Never commit to `main` directly.** Branch from it and open a PR.
- **PR titles** follow [Conventional Commits](https://www.conventionalcommits.org): `type(scope): subject`,
  with the subject starting lower-case. Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `chore`,
  `ci`, `build`, `test`, `style`. CI checks this.
- **CHANGELOG:** add an entry under `## [Unreleased]` in the repository's `CHANGELOG.md`. CI checks
  this; a maintainer can apply the `no-changelog` label when a change truly needs none.
- **Commit messages:** a conventional subject line, a paragraph on *why*, a list of the changes,
  then `Closes #N`.
- **Secrets never go in a repository.** In `deploy` they are sops-encrypted under `secrets/`, and CI
  rejects anything else.

Each repository's `README.md` and `CLAUDE.md` cover its own checks and conventions.
