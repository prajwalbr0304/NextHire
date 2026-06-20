"""
Stage-1 format guard. Wraps the official validate_submission.py rules so we
never submit a CSV that the server-side auto-validator would reject.
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUBMISSION = os.path.join(ROOT, "submission.csv")

HEADER = ["candidate_id", "rank", "score", "reasoning"]
CID = re.compile(r"^CAND_[0-9]{7}$")


def _read():
    with open(SUBMISSION, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def test_submission_exists():
    assert os.path.exists(SUBMISSION), "run rank.py to produce submission.csv first"


def test_header_exact():
    header, _ = _read()
    assert header == HEADER


def test_exactly_100_rows():
    _, data = _read()
    data = [r for r in data if any(c.strip() for c in r)]
    assert len(data) == 100


def test_ranks_unique_1_to_100():
    _, data = _read()
    ranks = sorted(int(r[1]) for r in data)
    assert ranks == list(range(1, 101))


def test_ids_valid_and_unique():
    _, data = _read()
    ids = [r[0] for r in data]
    assert all(CID.match(i) for i in ids)
    assert len(set(ids)) == 100


def test_score_non_increasing_with_tiebreak():
    _, data = _read()
    rows = sorted(((int(r[1]), float(r[2]), r[0]) for r in data), key=lambda x: x[0])
    for (r1, s1, c1), (r2, s2, c2) in zip(rows, rows[1:]):
        assert s1 >= s2, f"score increased from rank {r1} to {r2}"
        if s1 == s2:
            assert c1 <= c2, f"tie at ranks {r1},{r2} must break by candidate_id asc"


def test_reasoning_present_and_varied():
    _, data = _read()
    reasons = [r[3] for r in data]
    assert all(len(x.strip()) > 0 for x in reasons), "no empty reasoning"
    assert len(set(reasons)) >= 90, "reasoning should be substantively varied"
