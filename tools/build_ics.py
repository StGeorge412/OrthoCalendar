"""Build a subscribable calendar (.ics) from the liturgical calendar plus a parish's own events.

    python3 -I tools/build_ics.py --macro <calendar.json> [--parish events.csv] --out feed.ics
        [--tz America/New_York] [--alarm 60] [--name "St Example · Lent 2027"] [--link URL]

--macro   the liturgical ("macro") calendar: a calendar JSON as produced by Ascalon's
          tools/build_calendar.py + deconflict.py (one entry per day: name, fast, readings,
          commemorations, services, old_calendar).
--parish  the parish's own ("micro") events, a CSV with columns:
          date,start,end,title,location,notes   (date YYYY-MM-DD, times HH:MM local, end optional)
Macro days become all-day events; parish events become timed events, converted to UTC so every
calendar app shows them at the right local time. Standard library only.
"""
import argparse, csv, datetime as dt, hashlib, json, sys
from pathlib import Path
from zoneinfo import ZoneInfo

FAST = {
    "free": "No fast", "dairy": "Dairy, eggs and fish allowed (no meat)", "fish": "Fish, wine and oil allowed",
    "wine-oil": "Wine and oil allowed", "wine": "Wine allowed, no oil", "strict": "Strict fast",
}

def esc(s):
    return str(s).replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")

def fold(line):
    """RFC 5545: lines at most 75 octets, continuation lines start with a space."""
    out, b = [], line.encode("utf-8")
    while len(b) > (75 if not out else 74):   # continuation lines carry a leading space
        cut = 75 if not out else 74
        while cut > 0 and (b[cut] & 0xC0) == 0x80:   # never split a UTF-8 character
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n ".join(out)

def uid(*parts):
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:20] + "@orthocalendar"

def macro_events(days, link):
    for d in days:
        date = dt.date.fromisoformat(d["date"])
        fast = FAST.get(d.get("fast"), d.get("fast") or "")
        lines = []
        if d.get("subtitle"): lines.append(d["subtitle"])
        lines.append(f"Fast: {fast}" + (f" ({d['fast_note']})" if d.get("fast_note") else ""))
        if d.get("readings"): lines.append("Readings: " + " · ".join(d["readings"]) + (f" ({d['readings_note']})" if d.get("readings_note") else ""))
        if d.get("commemorations"): lines.append("Saints: " + " · ".join(d["commemorations"]))
        if d.get("services"): lines.append("Customary services: " + " · ".join(d["services"]) + " (check your parish's schedule)")
        oc = d.get("old_calendar") or {}
        if oc.get("date"):
            c = (oc.get("commemorations") or [""])[0]
            lines.append(f"Old Calendar: {oc['date']}" + (f" ({c})" if c and c != "—" else ""))
        if link: lines.append(link)
        summary = d["name"] + ("" if d.get("fast") in (None, "free") else f" · {fast}")
        yield [
            "BEGIN:VEVENT", f"UID:{uid('macro', d['date'])}",
            f"DTSTART;VALUE=DATE:{date:%Y%m%d}", f"DTEND;VALUE=DATE:{date + dt.timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{esc(summary)}", f"DESCRIPTION:{esc(chr(10).join(lines))}",
            "TRANSP:TRANSPARENT", "CATEGORIES:Liturgical calendar", "END:VEVENT",
        ]

def parish_events(path, tz, alarm):
    zone = ZoneInfo(tz)
    with open(path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            try:
                date = dt.date.fromisoformat(row["date"].strip())
                start = dt.datetime.combine(date, dt.time.fromisoformat(row["start"].strip()), zone)
                end = (dt.datetime.combine(date, dt.time.fromisoformat(row["end"].strip()), zone)
                       if row.get("end", "").strip() else start + dt.timedelta(hours=1))
            except (KeyError, ValueError) as e:
                sys.exit(f"{path}:{i}: bad row ({e}): {row}")
            utc = lambda t: t.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            ev = ["BEGIN:VEVENT", f"UID:{uid('parish', row['date'], row['start'], row['title'])}",
                  f"DTSTART:{utc(start)}", f"DTEND:{utc(end)}", f"SUMMARY:{esc(row['title'].strip())}",
                  "CATEGORIES:Parish"]
            if row.get("location", "").strip(): ev.append(f"LOCATION:{esc(row['location'].strip())}")
            if row.get("notes", "").strip(): ev.append(f"DESCRIPTION:{esc(row['notes'].strip())}")
            if alarm:
                ev += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(row['title'].strip())}",
                       f"TRIGGER:-PT{alarm}M", "END:VALARM"]
            yield ev + ["END:VEVENT"]

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--macro", required=True)
    ap.add_argument("--parish")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tz", default="America/New_York")
    ap.add_argument("--alarm", type=int, default=0, help="minutes before each parish event")
    ap.add_argument("--name", default="Orthodox calendar")
    ap.add_argument("--link", default="")
    ap.add_argument("--only-journal", action="store_true", help="macro days inside the journal range only")
    a = ap.parse_args()

    days = json.loads(Path(a.macro).read_text())["days"]
    if a.only_journal:
        days = [d for d in days if d.get("in_journal")]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AscalonX//OrthoCalendar//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(a.name)}", f"X-WR-TIMEZONE:{a.tz}"]
    n_macro = n_parish = 0
    for ev in macro_events(days, a.link):
        lines += ev[:2] + [f"DTSTAMP:{stamp}"] + ev[2:]; n_macro += 1
    if a.parish:
        for ev in parish_events(a.parish, a.tz, a.alarm):
            lines += ev[:2] + [f"DTSTAMP:{stamp}"] + ev[2:]; n_parish += 1
    lines.append("END:VCALENDAR")
    Path(a.out).write_text("\r\n".join(fold(l) for l in lines) + "\r\n", encoding="utf-8")
    print(f"wrote {a.out}: {n_macro} liturgical days, {n_parish} parish events")

if __name__ == "__main__":
    main()
