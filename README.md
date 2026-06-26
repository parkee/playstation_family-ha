# PlayStation Family Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for the **PlayStation Family** parental-controls API.
Monitor your children's PlayStation play-time and presence, set recurring and
today-only play-time limits, and adjust parental controls — directly from Home
Assistant.

> Unofficial and not affiliated with Sony. Built on the
> [`psnfamily`](https://pypi.org/project/psnfamily/) library, which is
> reverse-engineered from the PlayStation Family app.

## Features

One Home Assistant device is created per child, with:

| Entity | Platform | Description |
|--------|----------|-------------|
| Today's playtime limit | Number | **Today only** — set today's limit to any value (0 = clear the override / revert to the schedule) |
| Daily playtime limit | Number | Set the **recurring** limit on *every* weekday at once (0 = blocked, 15-minute steps) |
| `<Weekday>` playtime limit | Number ×7 | The recurring limit for one weekday (Monday…Sunday); editing one leaves the others untouched |
| `<Weekday>` playable from / until | Time ×14 | The playable-hours window (allowed hours / "bedtime") per weekday |
| When limit reached | Select | Action when the limit is hit: **Notify only** or **Log out** |
| Playtime used today | Sensor | Minutes played today |
| Playtime remaining | Sensor | Minutes of play-time left today |
| Online status | Sensor | Current PSN online status |
| Now playing | Sensor | Title currently being played, or "Not playing" |
| Last online | Sensor | Timestamp the child was last online |

The per-weekday limit and window entities are grouped under the device's
**Configuration** section. Data is polled from PSN every 2 minutes (cloud polling).

### Today vs. the recurring schedule

PSN has two distinct play-time controls, and so does this integration:

- **Today's playtime limit** (number) — a *one-day override* that sets today's
  limit to any value (e.g. `60` for 60 minutes today). Setting it to `0` clears
  the override, so today reverts to the recurring schedule.
- **The recurring weekly schedule** — mirrors the app's advanced schedule:
  - **Daily playtime limit** sets the same limit on every weekday at once.
  - The seven **`<Weekday>` playtime limit** numbers set each day individually.
  - The fourteen **`<Weekday>` playable from / until** times set each day's
    playable-hours window (full day = `00:00`–`23:59`, where `23:59` means
    end-of-day). `0` minutes on a day blocks play entirely that day.

`0` is **blocked**, never "unlimited" — a child has no play-time until you grant
it. Editing any single weekday entity preserves the rest of the schedule. For a
scripted one-day relative nudge, use the `adjust_today_playtime` service.

### "When limit reached" select

The **When limit reached** select controls what PlayStation does when a child
hits their daily play-time limit:

- **Notify only** – the child is warned but can keep playing.
- **Log out** – the child is signed out of PlayStation.

## Services

### `playstation_family.set_weekly_schedule`

Sets a child's recurring play-time limit independently for each weekday. Each
day's value is in **minutes** (0 or omitted = no limit that day, 15-minute
steps). An optional playable-hours window restricts *when* play is allowed
(minutes from local midnight; defaults to the full day, `0`–`1440`).

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | one of device/entity | — | The child's device (preferred) |
| `entity_id` | one of device/entity | — | Any entity belonging to the child |
| `monday`…`sunday` | no | 0 | Per-day limit in minutes (0 = no limit) |
| `window_start` | no | 0 | Playable window start, minutes from midnight |
| `window_end` | no | 1440 | Playable window end, minutes from midnight |

> **Weekday mapping:** `monday` is applied as schedule index 0 and `sunday` as
> index 6 (Monday-first, the order PSN's `ohanaUpdatePlaytimeSchedule` applies
> the 7-entry list).

Example — 2 h on weekdays, 4 h on weekends, only playable between 08:00 and
22:00:

```yaml
service: playstation_family.set_weekly_schedule
data:
  device_id: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
  monday: 120
  tuesday: 120
  wednesday: 120
  thursday: 120
  friday: 120
  saturday: 240
  sunday: 240
  window_start: 480   # 08:00
  window_end: 1320    # 22:00
```

### `playstation_family.adjust_today_playtime`

Adds or removes play-time **for today only** (a one-day override; does not touch
the recurring daily limit) — the scriptable form of the +15 / -15 buttons.
Positive minutes add, negative remove; rounded to 15-minute steps.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` / `entity_id` | one of | The child to adjust |
| `minutes` | yes | Minutes to add (positive) or remove (negative), ±480 max |

```yaml
service: playstation_family.adjust_today_playtime
data:
  device_id: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
  minutes: 30     # give 30 more minutes today (use -30 to take back)
```

### `playstation_family.set_parental_control`

Writes a single parental-control setting for a child. Values are PSN field codes.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` / `entity_id` | one of | The child to update |
| `field` | yes | One of `internetBrowser`, `vrApp`, `freeCommunication`, `contentControl`, `ageLevel`, `gameContent`, `spendingLimit`, `bluerayAgeContent`, `discContentCountry`, `dvdContent` |
| `value` | yes | The PSN code (e.g. `"1"` restrict / `"0"` allow for toggles; a level for `ageLevel`/`gameContent`; an amount for `spendingLimit`) |

```yaml
service: playstation_family.set_parental_control
data:
  device_id: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
  field: internetBrowser
  value: "1"      # restrict the web browser
```

## Installation via HACS

1. Open HACS in Home Assistant.
2. Click the three-dots menu → **Custom repositories**.
3. Add `https://github.com/parkee/playstation_family-ha` with category **Integration**.
4. Click **Install**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration → PlayStation Family**.
7. Enter your NPSSO token (see below).

## Getting your NPSSO token

The integration authenticates headlessly with an `npsso` cookie obtained from a
browser session:

1. Sign in at <https://www.playstation.com> as the **Family Manager** account
   (the adult that owns the family / parental controls).
2. In the **same browser**, open
   <https://ca.account.sony.com/api/v1/ssocookie>.
3. Copy the 64-character `npsso` value from the JSON response, e.g.:

   ```json
   { "npsso": "abcd...64chars...wxyz" }
   ```

4. Paste it into the integration's setup dialog.

The integration exchanges the npsso for an access token (~1 hour) and a refresh
token (~60 days) and refreshes automatically. You only need to repeat these
steps if you are asked to re-authenticate (when the refresh token eventually
expires).

## Notes

- You must use the **Family Manager** account. Other accounts can authenticate
  but cannot reach the Family API (you'll see a "scope unavailable" error).
- The PlayStation API self-throttles requests, so updates are not instantaneous.
- Daily limits are quantized to 15-minute increments by PlayStation.

## Requirements

- A PlayStation Family with at least one child account.
- The Family Manager account's NPSSO token.
- Home Assistant 2024.12 or later.
