#!/usr/bin/env bash
# pm-framework v1.0 (multi-repo org edition): reconcile labels and milestones in every repo listed
# in .github/project.yml, and validate the org's issue types and board fields. Non-destructive.
#
#   scripts/project-sync.sh --dry-run            # report drift; exit 0 none, 2 drift, 1 error
#   scripts/project-sync.sh                      # apply, then verify
#   scripts/project-sync.sh --dry-run --repo htg # one repo
#
# Auth: the ambient `gh` session (needs repo and read:project scopes; issue types need read:org).
# In CI, set PROJECT_ADMIN_TOKEN and it is used as GH_TOKEN.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${PROJECT_ADMIN_TOKEN:-}" ]]; then
  export GH_TOKEN="$PROJECT_ADMIN_TOKEN"
fi
exec python3 scripts/project_sync.py "$@"
