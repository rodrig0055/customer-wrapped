#!/usr/bin/env python3
"""Stage 3: the email merge file and template.

  IMAGE_BASE_URL=https://cdn.example.com/wrapped python manifest.py

Host out/pngs/ anywhere (S3, R2, a CDN) as <IMAGE_BASE_URL>/<cid>_<NN>_<key>.png, then load
out/manifest.csv into your email platform and paste out/email_template.html. Most platforms have no
conditionals, so every slot is fixed and a missing card points at a 1x1 transparent PNG, and the whole
greeting is pre-rendered per row.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SLOTS = ["archetype", "zodiac", "spend", "best_year", "type", "abroad", "night", "summary"]
BASE = os.environ.get("IMAGE_BASE_URL", "https://cdn.example.com/wrapped").rstrip("/")
BRAND = os.environ.get("BRAND_NAME", "Acme Florals")
SHOP_URL = os.environ.get("SHOP_URL", "https://acmeflorals.example")


def main():
    rows = []
    for line in open(os.path.join(OUT, "customers.jsonl")):
        c = json.loads(line)
        keys = ["archetype", *[x["key"] for x in c["cards"]], "summary"]
        url = {k: f"{BASE}/{c['cid']}_{i:02d}_{k}.png" for i, k in enumerate(keys, 1)}
        fn = c.get("first_name") or ""
        row = {"email": c["email"], "first_name": fn, "greeting": f"Hi {fn}," if fn else "Hi there,",
               "subject": f"{fn}, your {BRAND} Wrapped is here 🌷" if fn else f"Your {BRAND} Wrapped is here 🌷"}
        for i, k in enumerate(SLOTS, 1):
            row[f"url_{i}"] = url.get(k, f"{BASE}/transparent.png")
        rows.append(row)
    with open(os.path.join(OUT, "manifest.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    imgs = "".join(f'      <img src="{{{{url_{i}}}}}" width="408" style="width:100%;max-width:408px;display:block;'
                   f'border-radius:14px;margin:0 auto 14px;" alt="">\n' for i in range(1, len(SLOTS) + 1))
    tpl = f"""<!-- SUBJECT: {{{{subject}}}} -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fbeff0;"><tr><td align="center" style="padding:24px 12px;">
  <table role="presentation" width="440" cellpadding="0" cellspacing="0" style="width:440px;max-width:440px;background:#fff;border-radius:16px;font-family:Arial,Helvetica,sans-serif;">
    <tr><td align="center" style="padding:26px 28px 6px;">
      <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#d1495b;font-weight:bold;">{BRAND} &middot; Wrapped</div>
      <div style="font-size:26px;line-height:1.15;color:#5b2a86;font-weight:bold;margin-top:8px;">Your year in flowers. 🌷</div></td></tr>
    <tr><td align="center" style="padding:12px 30px 20px;"><div style="font-size:15px;line-height:1.5;color:#3b4453;">{{{{greeting}}}} thank you for sending love with us. <b>Press &amp; hold any card</b> to save it, then share it to your Story.</div></td></tr>
    <tr><td align="center" style="padding:0 16px;">
{imgs}    </td></tr>
    <tr><td align="center" style="padding:14px 30px 26px;"><a href="{SHOP_URL}" style="display:inline-block;background:#5b2a86;color:#fff;text-decoration:none;font-weight:bold;font-size:15px;padding:14px 30px;border-radius:999px;">Send someone flowers &rarr;</a></td></tr>
    <tr><td align="center" style="padding:16px 30px 24px;"><div style="font-size:11px;color:#8a93a1;"><a href="{{{{unsubscribe}}}}" style="color:#8a93a1;">Unsubscribe</a></div></td></tr>
  </table></td></tr></table>
"""
    open(os.path.join(OUT, "email_template.html"), "w").write(tpl)
    print(f"wrote out/manifest.csv ({len(rows)} rows) + out/email_template.html")


if __name__ == "__main__":
    main()
