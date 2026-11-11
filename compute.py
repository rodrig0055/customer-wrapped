#!/usr/bin/env python3
"""Stage 1: orders -> one recap per customer (out/customers.jsonl).

  python compute.py examples/orders.csv [--limit N] [--as-of YYYY-MM-DD]

Input: one row per delivered order with
  order_id, email, first_name, created_at (local time, ISO), delivery_date, total, items, message, sender_country
`items` is product names joined by "|". `sender_country` is set when the buyer paid from abroad.

Deterministic: no randomness; customers sorted by cid = sha1(lower(email))[:12], so the same input
gives byte-identical output and the same image filenames. Every exclusion rule lives in rules.py.
"""
import argparse
import bisect
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys

import rules as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CURRENCY = os.environ.get("CURRENCY_SYMBOL", "$")
HOME = os.environ.get("HOME_COUNTRY", "home")

# Approximate distance from each sender country to the shop, for the "distance your love travelled"
# card. Replace with your own market's table.
DISTANCE_KM = {"United Kingdom": ("🇬🇧", 5600), "Germany": ("🇩🇪", 6400), "Japan": ("🇯🇵", 10100),
               "Australia": ("🇦🇺", 15000), "Philippines": ("🇵🇭", 13800), "India": ("🇮🇳", 12500),
               "Mexico": ("🇲🇽", 3000), "Canada": ("🇨🇦", 1500), "Singapore": ("🇸🇬", 15300)}

ANIMALS = [("Rat", "🐭"), ("Ox", "🐂"), ("Tiger", "🐯"), ("Rabbit", "🐰"), ("Dragon", "🐉"), ("Snake", "🐍"),
           ("Horse", "🐴"), ("Goat", "🐐"), ("Monkey", "🐵"), ("Rooster", "🐓"), ("Dog", "🐶"), ("Pig", "🐷")]


def zodiac(year: int) -> tuple[str, str]:
    """Chinese zodiac animal of a calendar year (2020 was the Rat). Year-level is close enough for a card."""
    return ANIMALS[(year - 2020) % 12]


MOM = re.compile(r"\b(mom|mommy|momma|mama|mum|mother)\b")


def themes(m: str) -> dict:
    m = (m or "").lower()
    return dict(love=("love you" in m) or ("i love u" in m), bday=("happy birthday" in m) or ("happy bday" in m),
                anniv="anniversary" in m, mom=bool(MOM.search(m)), congrats="congrat" in m)


# Exactly eight archetypes. Every customer gets one; new behaviour is routed into these eight.
ARCHE = {
    "loyal": ("👑", "FLORAL<br>ROYALTY", "You don't need an occasion.<br>You have a standing order<br>with the universe."),
    "big_spender": ("💸", "THE BIG<br>SPENDER", "Budget says no.<br>Your heart says<br>add-to-cart everything!"),
    "last_minute": ("⚡", "LAST-MINUTE<br>LEGEND", "Cutting it close every time,<br>but your love still delivered."),
    "planner": ("🗓️", "THE PLANNER", "Occasion coming up?<br>You always got it. Show-off!"),
    "valentino": ("💘", "THE VALENTINO", "February 14 hits different<br>when you're built different."),
    "mom": ("💐", "MOM'S<br>FAVOURITE", "Mother's Day?<br>Ordered in advance,<br>every single year."),
    "birthday": ("🎂", "THE BIRTHDAY<br>REMINDER", "Calendars could never.<br>You always remember first,<br>with a surprise."),
    "thrifty": ("🌷", "THE SMART<br>SHOPPER", "Promo code ready<br>with every gift.<br>Icon behavior."),
}


def cid(email: str) -> str:
    return hashlib.sha1(email.encode()).hexdigest()[:12]


def load(path: str):
    """Aggregate qualifying orders per customer. Funeral and sensitive orders never count, and a
    customer with only those gets no recap at all."""
    agg, skipped, names = {}, collections.Counter(), {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            em = (r["email"] or "").strip().lower()
            if not em or not R.is_consumer(em) or R.mailability(em):
                skipped["not_a_mailable_consumer"] += 1
                continue
            names.setdefault(em, R.clean_first_name(r.get("first_name")))
            items = (r.get("items") or "").split("|")
            msg = r.get("message") or ""
            if any(R.is_funeral_product(i) for i in items) or R.is_funeral_message(msg):
                skipped["funeral"] += 1
                agg.setdefault(em, None)
                continue
            if R.is_sensitive_message(msg):
                skipped["sensitive"] += 1
                agg.setdefault(em, None)
                continue
            a = agg.get(em)
            if a is None:
                a = agg[em] = dict(o=0, spend=0.0, first=None, last=None, years=collections.Counter(), feb=0,
                                   lead_n=0, sameday=0, nextday=0, planner=0, night=0, hours=collections.Counter(),
                                   th=collections.Counter(), abroad=collections.Counter())
            a["o"] += 1
            a["spend"] += float(r.get("total") or 0)
            ca = dt.datetime.fromisoformat(r["created_at"])
            a["first"] = min(a["first"] or ca, ca)
            a["last"] = max(a["last"] or ca, ca)
            a["years"][ca.year] += 1
            if ca.hour >= 23 or ca.hour <= 5:
                a["night"] += 1
                a["hours"][ca.hour] += 1
            dd = dt.date.fromisoformat(r["delivery_date"]) if r.get("delivery_date") else None
            if dd and dd.month == 2 and 10 <= dd.day <= 16:
                a["feb"] += 1
            if dd:
                lead = (dd - ca.date()).days
                if -1 <= lead <= 120:
                    a["lead_n"] += 1
                    a["sameday"] += lead <= 0
                    a["nextday"] += lead == 1
                    a["planner"] += lead >= 2
            for k, v in themes(msg).items():
                a["th"][k] += v
            if r.get("sender_country") in DISTANCE_KM:
                a["abroad"][r["sender_country"]] += 1
    dropped = [e for e, a in agg.items() if a is None]
    for e in dropped:
        del agg[e]
    for e in [e for e, a in agg.items() if a["o"] >= 50]:   # reseller / corporate volume
        del agg[e]
    print(f"orders skipped: {dict(skipped)}; funeral/sensitive-only customers dropped: {len(dropped)}", file=sys.stderr)
    return agg, names


def top_share(arr, v):
    # Floor at 0.1: the single biggest spender otherwise rounds to "top 0.0%", which reads as a bug.
    return max(0.1, round((len(arr) - bisect.bisect_left(arr, v)) / len(arr) * 100, 1))


def fpct(x):
    return f"{x:g}"


def primary(a, B):
    o, ln, th = a["o"], a["lead_n"] or 1, a["th"]
    op, sp, aov = top_share(B["orders"], o), top_share(B["spend"], a["spend"]), a["spend"] / o
    if o >= 5 and len(a["years"]) >= 3 and op <= 8:
        return "loyal"
    if sp <= 8:
        return "big_spender"
    if a["sameday"] / ln >= 0.6:
        return "last_minute"
    if a["planner"] / ln >= 0.6 and a["lead_n"] >= 2:
        return "planner"
    if a["feb"] / o >= 0.4:
        return "valentino"
    if th["mom"] / o >= 0.34:
        return "mom"
    if th["bday"] / o >= 0.4:
        return "birthday"
    if o >= 3 and aov <= B["thrifty_aov"]:
        return "thrifty"
    cand = {"last_minute": a["sameday"] / ln, "planner": a["planner"] / ln, "valentino": a["feb"] / o,
            "mom": th["mom"] / o, "birthday": th["bday"] / o}
    k = max(cand, key=cand.get)
    if cand[k] > 0.15:
        return k
    # No signal: these are next-day senders, who already get the "RIGHT ON TIME" card. Never call them
    # Last-Minute Legends (that cover would contradict it), and never hand out the loyalty crown for one
    # order: on the real base that default once took 59,263 people, 54,071 of them with a single order.
    if o >= 5:
        return "loyal"
    return "thrifty" if aov <= B["thrifty_aov"] else "planner"


def stat_cards(a, arche, B, today):
    o, cards = a["o"], []
    yr = a["first"].year
    an, ae = zodiac(yr)
    elapsed = (today - a["first"].date()).days // 365      # elapsed time, not calendar years touched
    tt = max(0.1, round(bisect.bisect_left(B["first"], a["first"]) / len(B["first"]) * 100, 1))
    tsub = f"since {yr}" + (f" · {elapsed} year{'s' if elapsed > 1 else ''} with us" if elapsed >= 1 else "")
    if tt <= 30:
        tsub += f" · <b>top {fpct(tt)}%</b> longest-loving"
    cards.append({"key": "zodiac", "big": f"{ae} {an}", "label": f"You joined in the Year of the {an}", "sub": tsub})
    if a["spend"] >= R.SPEND_FLOOR:    # never brag about nothing
        sp = top_share(B["spend"], a["spend"])
        cards.append({"key": "spend", "big": f"{CURRENCY}{round(a['spend']):,}", "label": "spent making people feel loved",
                      "sub": f"That's the <b>top {fpct(sp)}%</b> of gift-givers 🌸" if sp <= 50 else "every cent, pure love 🌸"})
    by, bc = a["years"].most_common(1)[0]
    cards.append({"key": "best_year", "big": str(by),
                  "label": "your biggest year of love" if len(a["years"]) > 1 else "your first year with us",
                  "sub": f"<b>{bc}</b> gift{'s' if bc > 1 else ''} that year 🎁"})
    if a["lead_n"]:
        ln = a["lead_n"]
        sd, pl, nd = a["sameday"] / ln, a["planner"] / ln, a["nextday"] / ln
        one = ln == 1    # one order states the event, it does not claim a pattern
        if sd >= 0.5 and sd >= pl:
            cards.append({"key": "type", "big": "TYPE B", "label": "you love in the nick of time",
                          "sub": "your gift flew out <b>same-day</b> ⚡" if one else f"<b>{round(sd * 100)}%</b> of orders sent same-day ⚡"})
        elif pl >= 0.5:
            cards.append({"key": "type", "big": "TYPE A", "label": "always ahead of the occasion",
                          "sub": "sent <b>days in advance</b> 🗓️" if one else f"<b>{round(pl * 100)}%</b> of orders sent days in advance 🗓️"})
        elif round((sd + nd) * 100) > 0 and arche != "last_minute":
            cards.append({"key": "type", "big": "RIGHT<br>ON TIME", "label": "never late, never too early",
                          "sub": "delivered <b>right on the day</b> 🎯" if one else f"<b>{round((sd + nd) * 100)}%</b> arrived within a day 🎯"})
    if a["abroad"]:
        km = sum(DISTANCE_KM[c][1] * n for c, n in a["abroad"].items())   # cumulative, every country
        country, _ = max(a["abroad"].items(), key=lambda kv: (kv[1], kv[0]))
        more = len(a["abroad"]) - 1
        cards.append({"key": "abroad", "big": f"{km:,} km", "label": "the distance your love travelled 🌏",
                      "sub": f"from {DISTANCE_KM[country][0]} {country}" + (f" and {more} more" if more else "") + f", all the way {HOME}"})
    if a["night"] / o >= 0.35 and a["hours"]:
        h = a["hours"].most_common(1)[0][0]
        disp = "12 AM" if h == 0 else f"{h} AM" if h < 12 else "12 PM" if h == 12 else f"{h - 12} PM"
        cards.append({"key": "night", "big": disp, "label": "your most romantic hour 🌙",
                      "sub": "a true midnight sender 💌" if a["night"] >= 2 else "your gift was a midnight special 💌"})
    return cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("orders")
    ap.add_argument("--limit", type=int, default=0, help="first N customers by cid, for test runs")
    ap.add_argument("--as-of", default="", help="tenure is measured to this date (default today)")
    A = ap.parse_args()
    today = dt.date.fromisoformat(A.as_of) if A.as_of else dt.date.today()
    agg, names = load(A.orders)
    if not agg:
        sys.exit("no qualifying customers")
    aovs = sorted(a["spend"] / a["o"] for a in agg.values())
    B = {"orders": sorted(a["o"] for a in agg.values()), "spend": sorted(a["spend"] for a in agg.values()),
         "first": sorted(a["first"] for a in agg.values()), "thrifty_aov": aovs[len(aovs) // 4]}  # cheapest quarter
    rows = []
    for em, a in agg.items():
        k = primary(a, B)
        e2, name, meaning = ARCHE[k]
        rows.append({"cid": cid(em), "email": em, "first_name": names.get(em, ""), "archetype_key": k,
                     "archetype": {"emoji": e2, "name": name, "meaning": meaning},
                     "orders": a["o"], "spend": round(a["spend"]), "spend_pct": top_share(B["spend"], a["spend"]),
                     "currency": CURRENCY, "first_year": a["first"].year, "last_year": a["last"].year,
                     "cards": stat_cards(a, k, B, today)})
    rows.sort(key=lambda r: r["cid"])
    if A.limit:
        rows = rows[:A.limit]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "customers.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    mix = collections.Counter(r["archetype_key"] for r in rows)
    print(f"{len(rows)} recaps -> out/customers.jsonl; archetypes {dict(mix)}", file=sys.stderr)


if __name__ == "__main__":
    main()
