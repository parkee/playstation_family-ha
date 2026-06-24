# PlayStation Family Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for the **PlayStation Family** parental-controls API.
Monitor your children's PlayStation play-time and set their daily play-time
limits directly from Home Assistant.

> Unofficial and not affiliated with Sony. Built on the
> [`psnfamily`](https://pypi.org/project/psnfamily/) library, which is
> reverse-engineered from the PlayStation Family app.

## Features

One Home Assistant device is created per child, with:

| Entity | Platform | Description |
|--------|----------|-------------|
| Daily playtime limit | Number | Set/clear the daily play-time limit (0 = unlimited, 15-minute steps) |
| When limit reached | Select | Action when the limit is hit: **Notify only** or **Log out** |
| Playtime used today | Sensor | Minutes played today |
| Playtime remaining | Sensor | Minutes of play-time left today |
| Online status | Sensor | Current PSN online status |
| Now playing | Sensor | Title currently being played, or "Not playing" |
| Last online | Sensor | Timestamp the child was last online |

Data is polled from PSN every 2 minutes (cloud polling).

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
