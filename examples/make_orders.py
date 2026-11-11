"""Generate a synthetic order history for the demo: 800 invented customers of Acme Florals.

  python examples/make_orders.py        # writes examples/orders.csv

Each customer has a habit (last-minute sender, planner, Valentine's regular, Mother's Day regular,
big spender...) so every archetype and card shows up. A few rows exist to be excluded: sympathy
orders, a role address, a typo domain, a staff mailbox. Nobody here is real.
"""
import csv
import datetime as dt
import random
from pathlib import Path

rng = random.Random(8)
FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Ivy", "Lucas", "Nora", "Leo", "Mia", "Owen", "Ruby", "Eli",
         "Sofia", "Jack", "Chloe", "Sam", "Grace", "Theo", "Lena", "Max", "Isla", "Finn", "Aria", "Kai", "Elena", "Jude"]
LAST = ["Reyes", "Chen", "Patel", "Novak", "Garcia", "Kim", "Okafor", "Silva", "Larsen", "Moreau", "Tanaka", "Haddad"]
PRODUCTS = [("Sunflower Bouquet", 45), ("Blush Peony Jar", 79), ("Red Rose Dozen", 89), ("Candy Stripe Tulips", 48),
            ("Chocolate Drip Cake", 52), ("Celebration Gift Box", 65), ("Mini Succulent Trio", 26), ("Rainbow Roses", 72),
            ("Grand Orchid Arrangement", 160), ("Luxury Rose Box", 220)]
HABITS = ["random"] * 6 + ["last_minute", "planner", "valentino", "mom", "birthday", "thrifty", "big_spender", "loyal", "night", "abroad"]
COUNTRIES = ["United Kingdom", "Germany", "Japan", "Australia", "Philippines", "Canada"]
MSG = {"mom": "Happy Mother's Day mom, love you!", "birthday": "Happy birthday! Have the best day",
       "valentino": "Happy Valentine's, I love you", "random": "Thinking of you", "thrifty": "Thank you!"}


def second_sunday_may(y):
    d = dt.date(y, 5, 1)
    return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7)


def order(habit, year):
    if habit == "valentino":
        dd = dt.date(year, 2, 14)
    elif habit == "mom":
        dd = second_sunday_may(year)
    else:
        dd = dt.date(year, 1, 1) + dt.timedelta(days=rng.randrange(365))
    lead = {"last_minute": 0, "planner": rng.randint(3, 14), "valentino": rng.choice([0, 1, 3, 5]),
            "mom": rng.choice([0, 1, 1, 3])}.get(habit, rng.choice([0, 0, 1, 1, 1, 1, 2]))
    hour = rng.choice([23, 0, 1, 2]) if habit == "night" else rng.randint(8, 21)
    created = dt.datetime.combine(dd - dt.timedelta(days=lead), dt.time(hour, rng.randint(0, 59)))
    pool = PRODUCTS[-3:] if habit == "big_spender" else PRODUCTS[:4] + PRODUCTS[6:7] if habit == "thrifty" else PRODUCTS[:8]
    name, price = rng.choice(pool)
    if habit == "thrifty":
        price = round(price * 0.6)
    return created, dd, name, price, MSG.get(habit, MSG["random"])


def main():
    rows, oid = [], 100000
    for i in range(800):
        f, l = rng.choice(FIRST), rng.choice(LAST)
        email = f"{f.lower()}.{l.lower()}{i}@example.com"
        habit = rng.choice(HABITS)
        n = {"loyal": rng.randint(6, 14), "big_spender": rng.randint(3, 6), "random": rng.choice([1, 1, 1, 2, 3])}.get(habit, rng.randint(2, 5))
        start = rng.randint(2019, 2025)
        country = rng.choice(COUNTRIES) if habit == "abroad" else ""
        for k in range(n):
            year = min(2026, start + (k if habit in ("valentino", "mom", "loyal") else rng.randint(0, 2)))
            created, dd, name, price, msg = order(habit, year)
            if created.date() > dt.date(2026, 11, 1):
                continue
            oid += 1
            rows.append({"order_id": oid, "email": email, "first_name": rng.choice([f, f.upper(), f"{f} {l}", f"Ms. {f}"]),
                         "created_at": created.isoformat(timespec="minutes"), "delivery_date": dd.isoformat(),
                         "total": price + rng.choice([0, 5, 9]), "items": name, "message": msg, "sender_country": country})
    for email, item, msg in [("grace.okafor901@example.com", "Peaceful Standing Spray", "With deepest sympathy"),
                             ("info@example.com", "Sunflower Bouquet", ""), ("theo.kim902@gmail.con", "Red Rose Dozen", ""),
                             ("orders@acmeflorals.example", "Celebration Gift Box", "")]:
        oid += 1
        rows.append({"order_id": oid, "email": email, "first_name": "Test", "created_at": "2025-06-01T10:00",
                     "delivery_date": "2025-06-02", "total": 90, "items": item, "message": msg, "sender_country": ""})
    out = Path(__file__).with_name("orders.csv")
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} orders -> {out}")


if __name__ == "__main__":
    main()
