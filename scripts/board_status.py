#!/usr/bin/env python3
"""Keep the HTG Platform board's Status in step with the work (.github#52).

The board's own workflows move an item to Done when it closes; nothing moved work in between, so
the board lagged (2026-10-10). This reconciler reads every open issue on the board with the pull
requests that name it and its labels, and sets Status:

- **Verifying** while the issue carries the `verifying` label: built and live, waiting for the
  done-when's proof (a deploy, a live session, a date).
- **In Progress** when a pull request that is open or merged names the issue as work on it: a
  closing keyword ("Closes #N", any repo) or "Part of #N" / "Part of owner/repo#N".
  An item leaves Verifying for In Progress when the label comes off.
- **Done** for a closed issue the built-in workflow missed.

It never moves an item back to Todo and never touches pull-request items. `--report` lists what
it can't fix: In Progress with no open pull request and no activity for STALE_DAYS, and Verifying
for longer than STALE_DAYS. Without `--apply` it only prints what it would do.

    GH_TOKEN=... python3 scripts/board_status.py [--apply] [--report FILE]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field

OWNER = "hidden-token-gaming"
PROJECT = 1
LABEL = "verifying"
STALE_DAYS = 14
TODO, IN_PROGRESS, VERIFYING, DONE = "Todo", "In Progress", "Verifying", "Done"

QUERY = """
query($owner: String!, $number: Int!, $after: String) {
  organization(login: $owner) {
    projectV2(number: $number) {
      id
      field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } }
      items(first: 25, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          content {
            __typename
            ... on Issue {
              number url state updatedAt
              repository { nameWithOwner }
              labels(first: 30) { nodes { name } }
              timelineItems(itemTypes: [CROSS_REFERENCED_EVENT, LABELED_EVENT], last: 40) {
                nodes {
                  __typename
                  ... on CrossReferencedEvent {
                    willCloseTarget
                    source { ... on PullRequest { state number body repository { nameWithOwner } } }
                  }
                  ... on LabeledEvent { createdAt label { name } }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

MUTATION = """
mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(input: {projectId: $project, itemId: $item, fieldId: $field,
    value: {singleSelectOptionId: $option}}) { projectV2Item { id } }
}
"""

PART_OF = re.compile(r"(?i)\bpart of\s+(?:(?P<repo>[\w.-]+/[\w.-]+))?#(?P<num>\d+)\b")


@dataclass
class PR:
    repo: str
    number: int
    state: str  # OPEN, MERGED, CLOSED
    body: str
    closes: bool  # the reference is a closing keyword


@dataclass
class Item:
    item_id: str
    repo: str
    number: int
    url: str
    state: str  # OPEN, CLOSED
    status: str  # "" when unset
    updated: dt.datetime
    labels: set[str] = field(default_factory=set)
    labeled_at: dt.datetime | None = None  # when `verifying` was last added
    prs: list[PR] = field(default_factory=list)

    @property
    def ref(self) -> str:
        return f"{self.repo}#{self.number}"


def names_issue(pr: PR, item: Item) -> bool:
    """Whether a pull request names the issue as work on it."""
    if pr.closes:
        return True
    for m in PART_OF.finditer(pr.body or ""):
        repo = m.group("repo") or pr.repo
        if repo.lower() == item.repo.lower() and int(m.group("num")) == item.number:
            return True
    return False


def desired(item: Item) -> str | None:
    """The Status the item should have, or None to leave it as it is."""
    if item.state == "CLOSED":
        return DONE if item.status != DONE else None
    if LABEL in item.labels:
        return VERIFYING if item.status != VERIFYING else None
    worked = any(
        pr.state in ("OPEN", "MERGED") and names_issue(pr, item) for pr in item.prs
    )
    if item.status == VERIFYING:  # the label came off
        return IN_PROGRESS
    if item.status in ("", TODO) and worked:
        return IN_PROGRESS
    return None


def drift(item: Item, now: dt.datetime) -> str | None:
    """Why an item needs a person's look, or None."""
    if item.state != "OPEN":
        return None
    stale = now - dt.timedelta(days=STALE_DAYS)
    if item.status == VERIFYING and item.labeled_at and item.labeled_at < stale:
        return f"Verifying since {item.labeled_at:%Y-%m-%d}: is the proof in, or is something stuck?"
    if (
        item.status == IN_PROGRESS
        and item.updated < stale
        and not any(pr.state == "OPEN" and names_issue(pr, item) for pr in item.prs)
    ):
        return f"In Progress, no open pull request, quiet since {item.updated:%Y-%m-%d}: still being worked, waiting (label `verifying`), or back to Todo?"
    return None


def when(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


def parse(node: dict) -> Item | None:
    c = node.get("content") or {}
    if c.get("__typename") != "Issue":
        return None
    it = Item(
        item_id=node["id"],
        repo=c["repository"]["nameWithOwner"],
        number=c["number"],
        url=c["url"],
        state=c["state"],
        status=(node.get("fieldValueByName") or {}).get("name") or "",
        updated=when(c["updatedAt"]),
        labels={lab["name"] for lab in c["labels"]["nodes"]},
    )
    for ev in c["timelineItems"]["nodes"]:
        if (
            ev["__typename"] == "LabeledEvent"
            and (ev.get("label") or {}).get("name") == LABEL
        ):
            it.labeled_at = when(ev["createdAt"])
        elif ev["__typename"] == "CrossReferencedEvent":
            src = ev.get("source") or {}
            if (
                "number" in src
            ):  # a pull request (issues have no state MERGED and no body here)
                it.prs.append(
                    PR(
                        src["repository"]["nameWithOwner"],
                        src["number"],
                        src["state"],
                        src.get("body") or "",
                        bool(ev.get("willCloseTarget")),
                    )
                )
    return it


def gh_graphql(query: str, **variables) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        if v is None:
            continue
        args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
    out = subprocess.run(args, check=True, capture_output=True, text=True).stdout
    data = json.loads(out)
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"]))
    return data["data"]


def load() -> tuple[str, str, dict[str, str], list[Item]]:
    items, after = [], None
    while True:
        p = gh_graphql(QUERY, owner=OWNER, number=PROJECT, after=after)["organization"][
            "projectV2"
        ]
        for node in p["items"]["nodes"]:
            it = parse(node)
            if it:
                items.append(it)
        if not p["items"]["pageInfo"]["hasNextPage"]:
            break
        after = p["items"]["pageInfo"]["endCursor"]
    options = {o["name"]: o["id"] for o in p["field"]["options"]}
    return p["id"], p["field"]["id"], options, items


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--apply", action="store_true", help="set the Status; without it, only print"
    )
    ap.add_argument(
        "--report", metavar="FILE", help="write the drift report (Markdown) to FILE"
    )
    args = ap.parse_args(argv)

    project, status_field, options, items = load()
    missing = {s for s in (TODO, IN_PROGRESS, VERIFYING, DONE) if s not in options}
    if missing:
        print(f"the board's Status field lacks {sorted(missing)}", file=sys.stderr)
        if args.apply:
            return 2
    changes = 0
    for it in items:
        want = desired(it)
        if not want:
            continue
        changes += 1
        print(f"{it.ref}: {it.status or '(none)'} -> {want}")
        if args.apply:
            gh_graphql(
                MUTATION,
                project=project,
                item=it.item_id,
                field=status_field,
                option=options[want],
            )
    print(
        f"{len(items)} issues on the board, {changes} to change{'' if args.apply else ' (dry run)'}"
    )

    if args.report:
        now = dt.datetime.now(dt.UTC)
        rows = [(it, why) for it in items if (why := drift(it, now))]
        lines = [f"Board drift, {now:%Y-%m-%d}: {len(rows)} item(s) need a look.", ""]
        lines += [
            f"- [{it.ref}]({it.url}) ({it.status}): {why}"
            for it, why in sorted(rows, key=lambda r: r[0].ref)
        ]
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"report: {len(rows)} item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
