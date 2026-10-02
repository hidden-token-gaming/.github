# Changelog

All notable changes to the org-level `.github` repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- PM framework v1.0, multi-repo org edition: `.github/project.yml` declares every repo's labels and P0–P6 milestones, the org's issue types and the HTG Platform board's fields. `scripts/project-sync.sh` reconciles them non-destructively: a dry run exits 0 when there's no drift and 2 when there is, an API failure exits 1, and an apply ends with a verify pass. `docs/project-management.md` covers the deviation, the triage checklist and a runbook for what only the board UI can do. A reusable `labeler` workflow applies `component:*` labels by path, and this repo uses it with its own `.github/labeler.yml` (#3).
- Org scaffolding: profile README, default community-health files (code of conduct, contributing,
  security, support), issue forms per issue type (Epic, Feature, Task, Spike, Bug), a PR template,
  and reusable workflows for Conventional-Commit PR titles and the CHANGELOG `[Unreleased]` check
  with a `no-changelog` escape hatch, plus the handbook's markdownlint config (#2).

### Changed

- The org profile links gravel at `gravel-project/gravel` (#6).
