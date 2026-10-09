#!/usr/bin/env python3
"""Reconcile the org's GitHub PM objects with .github/project.yml (pm-framework v1.0, multi-repo).

Labels and milestones are created or updated in every repo the spec lists; nothing is ever
deleted. Org issue types and the board's fields are validated only. The exit code is the
contract: 0 means no drift, 2 means drift (a dry run found changes, or something can't be
fixed by this script), 1 means an error. An API failure is always an error, never "no drift".
"""

import argparse
import json
import subprocess
import sys
from urllib.parse import quote

import yaml


class SyncError(Exception):
    pass


def gh(*args, input=None):
    """Run gh and return its stdout; any failure raises, so a read can't pass for "no drift"."""
    r = subprocess.run(["gh", *args], input=input, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SyncError(f"gh {' '.join(args[:3])}…: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def gh_json(*args):
    out = gh(*args)
    return json.loads(out) if out.strip() else None


def gh_paged(path):
    """GET every page of a REST list."""
    out = gh("api", "--paginate", "--slurp", path)
    return [item for page in json.loads(out) for item in page]


class Report:
    def __init__(self, dry_run):
        self.dry_run = dry_run
        self.changes = 0  # fixable by this script
        self.manual = 0  # drift this script won't fix (issue types, board fields)

    def change(self, msg, *gh_args):
        """Count and print a change; outside a dry run, make it with gh."""
        self.changes += 1
        print(f"  {'would ' if self.dry_run else ''}{msg}")
        if not self.dry_run:
            gh(*gh_args)

    def drift(self, msg):
        self.manual += 1
        print(f"  DRIFT (fix by hand): {msg}")


def norm_color(c):
    return (c or "").lower().lstrip("#")


def sync_labels(rep, owner, repo, want):
    print(f"== {repo}: labels ==")
    live = {l["name"]: l for l in gh_paged(f"repos/{owner}/{repo}/labels?per_page=100")}
    target = f"repos/{owner}/{repo}/labels"
    for w in want:
        name, color, desc, frm = w["name"], norm_color(w["color"]), w.get("description", ""), w.get("from")
        if frm and frm in live and name not in live:
            rep.change(
                f"rename label {frm!r} → {name!r}",
                "api",
                "-X",
                "PATCH",
                f"{target}/{quote(frm, safe='')}",
                "-f",
                f"new_name={name}",
                "-f",
                f"color={color}",
                "-f",
                f"description={desc}",
            )
            continue
        cur = live.get(name)
        if cur is None:
            rep.change(
                f"create label {name!r}",
                "api",
                "-X",
                "POST",
                target,
                "-f",
                f"name={name}",
                "-f",
                f"color={color}",
                "-f",
                f"description={desc}",
            )
        elif norm_color(cur["color"]) != color or (cur.get("description") or "") != desc:
            diff = []
            if norm_color(cur["color"]) != color:
                diff.append(f"color {norm_color(cur['color'])} → {color}")
            if (cur.get("description") or "") != desc:
                diff.append(f"description {cur.get('description') or ''!r} → {desc!r}")
            rep.change(
                f"update label {name!r}: {'; '.join(diff)}",
                "api",
                "-X",
                "PATCH",
                f"{target}/{quote(name, safe='')}",
                "-f",
                f"color={color}",
                "-f",
                f"description={desc}",
            )
    unmanaged = sorted(set(live) - {w["name"] for w in want} - {w.get("from") for w in want})
    if unmanaged:
        print(f"  unmanaged (left alone): {', '.join(unmanaged)}")


def sync_milestones(rep, owner, repo, want):
    print(f"== {repo}: milestones ==")
    live = {m["title"]: m for m in gh_paged(f"repos/{owner}/{repo}/milestones?state=all&per_page=100")}
    for w in want:
        # state: open (the default) or closed, once a phase's gate is met and its issues are done.
        title, desc, state = w["title"], w.get("description", ""), w.get("state", "open")
        if state not in ("open", "closed"):
            raise SystemExit(f"milestone {title!r}: state must be open or closed, not {state!r}")
        cur = live.get(title)
        if cur is None:
            rep.change(
                f"create milestone {title!r}" + (" (closed)" if state == "closed" else ""),
                "api",
                "-X",
                "POST",
                f"repos/{owner}/{repo}/milestones",
                "-f",
                f"title={title}",
                "-f",
                f"description={desc}",
                "-f",
                f"state={state}",
            )
            continue
        changed = []
        if (cur.get("description") or "") != desc:
            changed.append("description")
        if cur.get("state") != state:
            if state == "closed" and cur.get("open_issues", 0) > 0:
                print(f"  milestone {title!r}: declared closed but has {cur['open_issues']} open issue(s); left open")
            else:
                changed.append(f"state {cur.get('state')} -> {state}")
        if changed:
            args = ["-f", f"description={desc}"]
            if any(c.startswith("state") for c in changed):
                args += ["-f", f"state={state}"]
            rep.change(
                f"update milestone {title!r}: {', '.join(changed)}",
                "api",
                "-X",
                "PATCH",
                f"repos/{owner}/{repo}/milestones/{cur['number']}",
                *args,
            )
    unmanaged = sorted(set(live) - {w["title"] for w in want})
    if unmanaged:
        print(f"  unmanaged (left alone): {', '.join(unmanaged)}")


def check_issue_types(rep, owner, want):
    print("== org issue types (validate-only) ==")
    live = {t["name"]: t for t in gh_json("api", f"orgs/{owner}/issue-types")}
    for w in want:
        cur = live.get(w["name"])
        if cur is None:
            rep.drift(f"issue type {w['name']!r} is missing")
        elif (cur.get("description") or "") != w.get("description", ""):
            rep.drift(f"issue type {w['name']!r} description is {cur.get('description')!r}")


FIELDS_QUERY = """
query($owner: String!, $number: Int!) {
  organization(login: $owner) {
    projectV2(number: $number) {
      title
      fields(first: 100) {
        nodes {
          ... on ProjectV2FieldCommon { name dataType }
          ... on ProjectV2SingleSelectField { options { name } }
        }
      }
    }
  }
}"""


def check_project(rep, p):
    print(f"== board #{p['number']} (validate-only) ==")
    data = gh_json(
        "api",
        "graphql",
        "-f",
        f"query={FIELDS_QUERY}",
        "-f",
        f"owner={p['owner']}",
        "-F",
        f"number={p['number']}",
    )
    proj = (((data or {}).get("data") or {}).get("organization") or {}).get("projectV2")
    if proj is None:
        raise SyncError(f"can't read board #{p['number']} of {p['owner']} (needs the read:project scope)")
    if proj["title"] != p.get("title", proj["title"]):
        rep.drift(f"board title is {proj['title']!r}")
    live = {f["name"]: f for f in proj["fields"]["nodes"] if f}
    for w in p.get("fields", []):
        cur = live.get(w["name"])
        if cur is None:
            rep.drift(f"field {w['name']!r} is missing")
            continue
        if cur["dataType"].lower() != w["type"]:
            rep.drift(f"field {w['name']!r} is {cur['dataType'].lower()}, not {w['type']}")
        if "options" in w and [o["name"] for o in cur.get("options") or []] != w["options"]:
            rep.drift(f"field {w['name']!r} options are {[o['name'] for o in cur.get('options') or []]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="report drift without changing anything")
    ap.add_argument("--repo", action="append", help="limit to these repos (repeatable)")
    ap.add_argument("spec", nargs="?", default=".github/project.yml")
    args = ap.parse_args()

    with open(args.spec) as f:
        spec = yaml.safe_load(f)
    if spec.get("framework_version") != "1.0" or spec.get("mode") != "org":
        raise SyncError("this reconciler reads framework_version 1.0, mode org")
    owner = spec["owner"]
    repos = spec["repos"]
    validate_limits(spec)
    if args.repo:
        unknown = set(args.repo) - set(repos)
        if unknown:
            raise SyncError(f"not in the spec: {', '.join(sorted(unknown))}")
        repos = {r: repos[r] for r in args.repo}

    rep = run(spec, owner, repos, args.dry_run, check_org=not args.repo, label=args.spec)
    if rep.changes == 0 and rep.manual == 0:
        print("No drift.")
        return 0
    verb = "to make" if args.dry_run else "made"
    print(f"{rep.changes} change(s) {verb}; {rep.manual} to fix by hand.")
    if args.dry_run or rep.manual:
        return 2
    # Verify: a second, read-only pass must find nothing left to change.
    print("Verifying…")
    again = run(spec, owner, repos, True, check_org=False, label=args.spec)
    if again.changes:
        print(f"error: {again.changes} change(s) still pending after apply", file=sys.stderr)
        return 1
    print("Verified: no drift.")
    return 0


LABEL_DESCRIPTION_MAX = 100  # GitHub rejects longer ones with a 422 only when the label is created


def validate_limits(spec):
    """Fail at load time on anything GitHub would reject mid-apply, so a dry run catches it."""
    too_long = []
    for lab in spec.get("labels", []):
        if len(lab.get("description") or "") > LABEL_DESCRIPTION_MAX:
            too_long.append(lab["name"])
    for repo, cfg in spec["repos"].items():
        for c, d in (cfg.get("components") or {}).items():
            if len(d or "") > LABEL_DESCRIPTION_MAX:
                too_long.append(f"{repo} component:{c}")
    if too_long:
        raise SyncError(
            f"label description over {LABEL_DESCRIPTION_MAX} characters: {', '.join(too_long)}"
        )


def run(spec, owner, repos, dry_run, check_org, label):
    rep = Report(dry_run)
    print(f"Reconciling {owner} from {label}{' (dry run)' if dry_run else ''}")
    for repo, cfg in repos.items():
        comps = [
            {"name": f"component:{c}", "color": spec["component_color"], "description": d}
            for c, d in (cfg.get("components") or {}).items()
        ]
        sync_labels(rep, owner, repo, spec.get("labels", []) + comps)
        sync_milestones(rep, owner, repo, spec.get("milestones", []))
    if check_org:
        check_issue_types(rep, owner, spec.get("issue_types", []))
        if spec.get("project"):
            check_project(rep, spec["project"])
    return rep


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SyncError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
