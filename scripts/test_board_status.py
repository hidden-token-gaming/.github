"""Unit tests for board_status's decisions (python3 -m unittest discover -s scripts)."""

import datetime as dt
import unittest

import board_status as bs

NOW = dt.datetime(2026, 10, 10, 18, 0, tzinfo=dt.UTC)


def item(
    status="Todo",
    state="OPEN",
    labels=(),
    prs=(),
    updated=NOW,
    labeled_at=None,
    repo="hidden-token-gaming/htg",
    number=57,
):
    return bs.Item(
        "I",
        repo,
        number,
        f"https://github.com/{repo}/issues/{number}",
        state,
        status,
        updated,
        set(labels),
        labeled_at,
        list(prs),
    )


def pr(state="OPEN", body="", closes=False, repo="hidden-token-gaming/htg", number=1):
    return bs.PR(repo, number, state, body, closes)


class NamesIssue(unittest.TestCase):
    def test_closing_keyword(self):
        self.assertTrue(bs.names_issue(pr(closes=True), item()))

    def test_part_of_same_repo(self):
        self.assertTrue(bs.names_issue(pr(body="Part of #57"), item()))

    def test_part_of_another_repo(self):
        it = item(repo="hidden-token-gaming/htg", number=57)
        self.assertTrue(
            bs.names_issue(
                pr(
                    body="Part of hidden-token-gaming/htg#57",
                    repo="gravel-project/gravel",
                ),
                it,
            )
        )
        self.assertFalse(
            bs.names_issue(pr(body="Part of #57", repo="gravel-project/gravel"), it),
            "a bare #57 in gravel is gravel's #57",
        )

    def test_mentions_are_not_work(self):
        for body in ["See #57", "follow-up filed as #57", "Part of #570", "part of #5"]:
            self.assertFalse(bs.names_issue(pr(body=body), item()), body)


class Desired(unittest.TestCase):
    def test_open_or_merged_work_moves_todo(self):
        self.assertEqual(bs.desired(item(prs=[pr(body="Part of #57")])), bs.IN_PROGRESS)
        self.assertEqual(
            bs.desired(item(status="", prs=[pr(state="MERGED", closes=True)])),
            bs.IN_PROGRESS,
        )

    def test_closed_unmerged_pr_moves_nothing(self):
        self.assertIsNone(bs.desired(item(prs=[pr(state="CLOSED", closes=True)])))

    def test_label_wins_and_leaving_it_returns(self):
        self.assertEqual(
            bs.desired(item(status="In Progress", labels=["verifying"])), bs.VERIFYING
        )
        self.assertIsNone(bs.desired(item(status="Verifying", labels=["verifying"])))
        self.assertEqual(bs.desired(item(status="Verifying")), bs.IN_PROGRESS)

    def test_closed_goes_done_once(self):
        self.assertEqual(
            bs.desired(item(state="CLOSED", status="In Progress")), bs.DONE
        )
        self.assertIsNone(bs.desired(item(state="CLOSED", status="Done")))

    def test_never_back_to_todo(self):
        self.assertIsNone(bs.desired(item(status="In Progress")))


class Drift(unittest.TestCase):
    old = NOW - dt.timedelta(days=bs.STALE_DAYS + 1)

    def test_quiet_in_progress(self):
        self.assertIn(
            "no open pull request",
            bs.drift(item(status="In Progress", updated=self.old), NOW),
        )
        self.assertIsNone(
            bs.drift(
                item(
                    status="In Progress", updated=self.old, prs=[pr(body="Part of #57")]
                ),
                NOW,
            ),
            "an open PR is work",
        )
        self.assertIsNone(bs.drift(item(status="In Progress"), NOW), "recent activity")

    def test_long_verifying(self):
        self.assertIn(
            "Verifying since",
            bs.drift(
                item(status="Verifying", labels=["verifying"], labeled_at=self.old), NOW
            ),
        )
        self.assertIsNone(
            bs.drift(
                item(status="Verifying", labels=["verifying"], labeled_at=NOW), NOW
            )
        )

    def test_closed_is_not_drift(self):
        self.assertIsNone(
            bs.drift(item(status="In Progress", state="CLOSED", updated=self.old), NOW)
        )


class Parse(unittest.TestCase):
    def test_issue_node(self):
        node = {
            "id": "PVTI",
            "fieldValueByName": {"name": "Todo"},
            "content": {
                "__typename": "Issue",
                "number": 57,
                "url": "u",
                "state": "OPEN",
                "updatedAt": "2026-10-10T12:00:00Z",
                "repository": {"nameWithOwner": "hidden-token-gaming/htg"},
                "labels": {"nodes": [{"name": "verifying"}]},
                "timelineItems": {
                    "nodes": [
                        {
                            "__typename": "LabeledEvent",
                            "createdAt": "2026-10-09T12:00:00Z",
                            "label": {"name": "verifying"},
                        },
                        {
                            "__typename": "CrossReferencedEvent",
                            "willCloseTarget": False,
                            "source": {
                                "state": "MERGED",
                                "number": 122,
                                "body": "Part of hidden-token-gaming/htg#57",
                                "repository": {
                                    "nameWithOwner": "gravel-project/gravel"
                                },
                            },
                        },
                        {
                            "__typename": "CrossReferencedEvent",
                            "willCloseTarget": False,
                            "source": {},
                        },
                    ]
                },
            },
        }
        it = bs.parse(node)
        self.assertEqual(
            (it.ref, it.status, it.labels, len(it.prs)),
            ("hidden-token-gaming/htg#57", "Todo", {"verifying"}, 1),
        )
        self.assertEqual(it.labeled_at.day, 9)
        self.assertTrue(bs.names_issue(it.prs[0], it))

    def test_pull_request_items_are_skipped(self):
        self.assertIsNone(
            bs.parse({"id": "x", "content": {"__typename": "PullRequest"}})
        )


if __name__ == "__main__":
    unittest.main()
