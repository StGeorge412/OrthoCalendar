# OrthoCalendar
Project to build a way for parishes to integrate larger calendar information from GOARCH and their own local parish information.  


The Problem I'm solving.  Father sends out a church bulletin every week with a schedule. I just got one for Pascha.  It's 4 pages.  Edited in word.  

I thought, why not have an online calendar that father can put his notes into, and people can subscribe to or get alerts to?  I went to the calendar on the church's website, it wasn't really that robust.  I thought, well GOARCH has a nice calendar view.  Wouldn't it be cool if we could use that format, and put in our own events? Matins, Liturgy times, trisagions, meals, vespers, picnics, outings, etc.

One major calendar that has the macro calendar, and the micro.

## How it works now

Two layers, one feed:

- **Macro: the liturgical calendar.** Feasts, fasting, readings, saints and customary services for each day. The first source is Ascalon's calendar engine (`Archetype/ascalon/tools/build_calendar.py` + `deconflict.py`). It builds each day from the OCA calendar, then reconciles it with GOARCH/Antiochian usage; see `ascalon/docs/calendar-policy.md`.
- **Micro: the parish.** Father's own events (Matins, Liturgy times, trisagia, meals, vespers, picnics, outings) in a simple spreadsheet: `date,start,end,title,location,notes`.

`tools/build_ics.py` merges them into one subscribable `.ics` file. People add it once in Google, Apple or Outlook Calendar, and get every liturgical day plus every parish event, with optional reminders.

```sh
python3 -I tools/build_ics.py --macro ../../../Desktop/Archetype/ascalon/data/calendar-2027.json \
  --parish examples/example-parish-holy-week.csv --alarm 60 \
  --name "St Example · Great Lent 2027" --out examples/example-parish-lent-2027.ics
```

`examples/example-parish-holy-week.csv` uses made-up times; replace them with the parish's real schedule.

## How it fits with Ascalon

Ascalon (the Lent journal and the full-year planner) and OrthoCalendar share one calendar engine:

- **The journal** prints the macro calendar on paper, one day per spread.
- **OrthoCalendar** publishes the same days as a feed and adds the parish's events.
- **The parish pack** for the Lent journal includes a feed the parish can post on its website. One priest's yes puts the calendar, and a link to the journal, in every parishioner's phone.

**Next step for the engine:** today it covers Lent 2027 only. Making it cover the full year is needed anyway for the planner, which starts at the Church New Year on 1 September 2027. When that happens, the engine should move into this repo, with Ascalon depending on it.

## Data rules

- **Facts only from other calendars.** Dates, names of saints and scripture citations can be used. The texts on goarch.org and oca.org (lives of saints, readings, hymns) are copyrighted, so they're not copied.
- **goarch.org is behind a bot check.** Don't scrape it. For a real product, ask the GOARCH Department of Internet Ministries (which runs the Online Chapel) for a data feed or permission. The Antiochian Archdiocese's site uses GOARCH's data.
- **New Calendar by default**, with Old Calendar dates noted. Fasting shows the general rule, and the parish's priest decides.

## Roadmap (gated: nothing here ships before the Ascalon Lent journal, on sale 6 Jan 2027)

1. **Done.** Macro + micro merged into an `.ics` feed (`tools/build_ics.py`).
2. **Candidate v0 feature: the weekly bulletin, generated.** Father enters the week's events once, and gets a printable bulletin PDF and the calendar feed from the same data. This reuses Ascalon's print pipeline, and it's the problem this README starts with.
3. **Later:** a simple editing page for Father instead of a spreadsheet; hosted feeds per parish; reminders by text or email; more than one parish.
