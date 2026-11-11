import csv
import json
import subprocess
import sys
from pathlib import Path

import rules as R

ROOT = Path(__file__).resolve().parent.parent


def test_consumer_and_mailability():
    assert R.is_consumer("ava@gmail.com") and R.is_consumer("prof@uni.edu")
    assert not R.is_consumer("orders@acmeflorals.example")          # own domain
    assert not R.is_consumer("ceo@bigcorp.com")                      # business
    assert R.mailability("info@gmail.com") == "role_address"
    assert R.mailability("ava@gmail.con") == "typo_domain"
    assert R.mailability("x@mailinator.com") == "disposable"
    assert R.correct_domain("gmial.com") == "gmail.com"


def test_sensitive():
    assert R.is_funeral_product("Peaceful Standing Spray")
    assert not R.is_funeral_product("Christmas Wreath")              # seasonal, not sympathy
    assert R.is_funeral_message("With deepest sympathy")
    assert R.is_sensitive_message("so sorry about the miscarriage")


def test_names():
    assert R.clean_first_name("MARIA SANTOS") == "Maria"
    assert R.clean_first_name("Dr. Ava Reyes") == "Ava"
    assert R.clean_first_name("test") == ""
    assert R.clean_first_name("ava@gmail.com") == ""


def test_compute_end_to_end(tmp_path):
    subprocess.run([sys.executable, "examples/make_orders.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "compute.py", "examples/orders.csv", "--as-of", "2026-11-11"], cwd=ROOT, check=True)
    rows = [json.loads(l) for l in open(ROOT / "out/customers.jsonl")]
    emails = {r["email"] for r in rows}
    assert "grace.okafor901@example.com" not in emails               # sympathy-only customer gets no recap
    assert not any("acmeflorals" in e or e.startswith("info@") for e in emails)
    assert len({r["archetype_key"] for r in rows}) == 8               # every archetype shows up
    assert [r["cid"] for r in rows] == sorted(r["cid"] for r in rows) # deterministic order
    for r in rows:
        spend = [c for c in r["cards"] if c["key"] == "spend"]
        assert not spend or r["spend"] >= R.SPEND_FLOOR               # never brag about nothing
