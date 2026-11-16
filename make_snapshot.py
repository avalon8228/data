#!/usr/bin/env python3
"""สร้างหน้า calendar-list.html (HTML ธรรมดา ไม่ใช้ JavaScript) จากตาราง calendar_events ใน Supabase
อ่านค่าเชื่อมต่อจาก config.js ในโฟลเดอร์เดียวกัน (publishable key ที่เปิดเผยได้ ไม่ต้องตั้ง secret เพิ่ม)"""
import json, os, re, sys, urllib.error, urllib.request
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "calendar-list.html")
MN = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
MS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
WD = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"]
MEAN = {"XD": "ไม่ได้สิทธิรับเงินปันผล", "XR": "ไม่ได้สิทธิจองซื้อหุ้นออกใหม่", "XW": "ไม่ได้สิทธิรับใบสำคัญแสดงสิทธิ (Warrant)",
        "XT": "ไม่ได้สิทธิรับใบสำคัญแสดงสิทธิจองซื้อหุ้นเพิ่มทุนที่โอนสิทธิได้", "XM": "ไม่มีสิทธิเข้าประชุมผู้ถือหุ้น",
        "XE": "ไม่ได้สิทธิแปลงสภาพตราสารสิทธิเป็นหุ้นอ้างอิง", "XN": "ไม่มีสิทธิรับเงินคืนจากการลดทุน", "XB": "ไม่ได้สิทธิในบางกรณี"}
LABEL = {"MEET": "การจัดประชุมผู้ถือหุ้น"}
ORDER = ["XD", "XM", "XR", "MEET"]
TS = "<!--TS--><!--/TS-->"


def config():
    txt = open(os.path.join(HERE, "config.js"), encoding="utf-8").read()
    g = lambda k: re.search(k + r"\s*[:=]\s*['\"]([^'\"]+)['\"]", txt).group(1)
    return g("SUPABASE_URL").rstrip("/"), g("SUPABASE_KEY")


def fetch_all(base, key):
    headers = {"apikey": key, "User-Agent": "calendar-snapshot/1.0"}
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    rows, off = [], 0
    while True:
        url = f"{base}/rest/v1/calendar_events?select=event_date,mark,symbol&order=event_date.asc,symbol.asc&limit=1000&offset={off}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            part = json.loads(r.read().decode("utf-8"))
        rows += part
        if len(part) < 1000:
            return rows
        off += 1000


def build(rows):
    by = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["event_date"], r["symbol"])):
        by.setdefault(r["event_date"], OrderedDict()).setdefault(r["mark"], []).append(r["symbol"])
    out = ['<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>รายการปฏิทินหลักทรัพย์ (ข้อความ)</title><style>",
           ":root{color-scheme:light dark}body{font:16px/1.6 system-ui,'Noto Sans Thai',sans-serif;max-width:760px;margin:0 auto;padding:1rem}",
           "h2{margin:1.8rem 0 .3rem;border-bottom:2px solid #f5a623}h3{margin:1rem 0 .1rem;font-size:1rem}ul{margin:.1rem 0;padding-left:1.2rem}small{opacity:.7}",
           "</style></head><body>",
           '<p><a href="calendar.html">← ปฏิทิน (หน้าแก้ไข)</a></p><h1>รายการปฏิทินหลักทรัพย์</h1>',
           f"<p>อัปเดตข้อมูลล่าสุด: {TS} (เวลาไทย) · รวม {len(rows)} รายการ · "
           "หน้านี้เป็นข้อความธรรมดา สร้างจากข้อมูลบนหน้าปฏิทินของทีมโดยอัตโนมัติ (ตรวจทุกชั่วโมง)</p>"]
    cur = None
    for d, marks in by.items():
        dt = date.fromisoformat(d)
        if d[:7] != cur:
            cur = d[:7]
            out.append(f"<h2>{MN[dt.month - 1]} {dt.year + 543}</h2>")
        out.append(f"<h3>{dt.day} {MS[dt.month - 1]} {dt.year + 543} ({WD[(dt.weekday() + 1) % 7]})</h3><ul>")
        for k in [k for k in ORDER if k in marks] + sorted(k for k in marks if k not in ORDER):
            mean = f" <small>{escape(MEAN[k])}</small>" if k in MEAN else ""
            out.append(f"<li><b>{escape(LABEL.get(k, k))}</b>{mean}: {escape(', '.join(marks[k]))}</li>")
        out.append("</ul>")
    out.append("</body></html>")
    return "\n".join(out)


def main():
    base, key = config()
    try:
        rows = fetch_all(base, key)
    except (urllib.error.URLError, ValueError) as e:
        sys.exit(f"อ่านข้อมูลจาก Supabase ไม่ได้: {e}")
    if not rows:
        sys.exit("ไม่พบข้อมูลในตาราง (หรืออ่านไม่ได้เพราะสิทธิ RLS) ไม่เขียนทับหน้าเดิม")
    body = build(rows)
    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if re.sub(r"<!--TS-->.*?<!--/TS-->", TS, old, flags=re.S) == body:
        return print("ไม่มีการเปลี่ยนแปลง")
    now = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M")
    open(OUT, "w", encoding="utf-8").write(body.replace(TS, f"<!--TS-->{now}<!--/TS-->"))
    print(f"สร้าง {OUT} จาก {len(rows)} รายการ")


if __name__ == "__main__":
    main()
