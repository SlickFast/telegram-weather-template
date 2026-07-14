# ☀️ Telegram Weather Dashboard — powered by SlickFast

**A beautiful weather dashboard, delivered to your Telegram every morning. No server, no
frameworks — one Python file, GitHub Actions, and [SlickFast](https://slickfast.com).**

Current temp + feels-like, chance of rain, wind, humidity, an hourly temperature curve, and
the 7-day forecast — rendered as one crisp retina image by the SlickFast API and sent to your
chat while you're waking up.

Works for **any city on Earth** (weather data by [Open-Meteo](https://open-meteo.com), free,
no key needed).

## Setup — about 5 minutes

**1. Use this template** → click the green **"Use this template"** button above → create your
own copy (private is fine).

**2. Make a Telegram bot** → message [@BotFather](https://t.me/BotFather) in Telegram → send
`/newbot` → follow the prompts → copy the **token** it gives you.

**3. Add your three secrets** → your repo → Settings → Secrets and variables → Actions →
**Secrets** tab → New repository secret:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `SLICKFAST_API_KEY` | free key from [slickfast.com](https://slickfast.com) (250 renders/mo, no card — a daily send uses ~30) |
| `TELEGRAM_CHAT_ID` | see step 4 👇 |

**4. Find your chat id** → in Telegram, **send your new bot any message** (it can't message
you first). Then: repo → Actions → **weather** → Run workflow → mode: `discover` → open the
run's log — it prints your `chat_id`. Add it as the `TELEGRAM_CHAT_ID` secret.

**5. Set your city** → Settings → Secrets and variables → Actions → **Variables** tab:

| Variable | Example | Notes |
|---|---|---|
| `CITY` | `Berlin` | the title on the dashboard |
| `LATITUDE` | `52.52` | [find yours](https://open-meteo.com/en/docs) |
| `LONGITUDE` | `13.41` | |
| `TIMEZONE` | `Europe/Berlin` | IANA name |
| `UNITS` | `metric` | `metric` (°C, km/h) or `imperial` (°F, mph) |

*(Skip this step and you get the default city: Asunción, Paraguay — the city this template
was born for.)*

**6. Test it** → Actions → weather → Run workflow → mode: `send`. Check your Telegram. ☀️

From then on it runs daily on the schedule in
[`.github/workflows/weather.yml`](.github/workflows/weather.yml) — edit the cron line to
change your delivery time.

## Make it yours

- **Colors** — four hex values at the top of [`weather.py`](weather.py) (`BG`, `TILE`, `GRN`,
  `PINK`) restyle the whole board.
- **Layout & charts** — the dashboard is one JSON spec in `build_spec()`. Add tiles, swap
  chart types, resize — every option is in the
  [SlickFast chart-spec reference](https://github.com/SlickFast/slickfast/blob/main/packages/render-core/SPEC.md).
- **Delivery time** — the `cron` line in the workflow (UTC). Tip: use an odd minute; GitHub's
  scheduler is congested at :00 and runs can drift late — fine for a morning brief.

## Good-to-knows

- The bot **uploads the image bytes** (multipart `sendPhoto`) instead of sending a URL —
  Telegram caches photos by URL, so uploading keeps every send fresh.
- GitHub pauses schedules in repos with **no activity for 60 days** — a single commit wakes
  it back up.
- Everything here is stdlib Python — no `pip install`, no dependencies, nothing to maintain.

---

Made with [SlickFast](https://slickfast.com) — charts & dashboards for AI agents and
automations. JSON spec in → retina image out, in milliseconds.
