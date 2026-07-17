#!/usr/bin/env python3
# Daily weather dashboard → Telegram, rendered by SlickFast. Stdlib only, no server.
#
# Modes:  discover  → print the chat ids your bot can see (message the bot first!)
#         send      → fetch weather, render via api.slickfast.com, send to your chat
#         live      → publish/refresh a LIVE chart URL instead (no Telegram needed) —
#                     embed the printed URL in a README or webpage; re-runs keep it fresh
#
# Configure via env (see .github/workflows/weather.yml — GitHub Variables/Secrets):
#   TELEGRAM_BOT_TOKEN  (secret)  from @BotFather
#   TELEGRAM_CHAT_ID    (secret)  find yours with the discover mode
#   SLICKFAST_API_KEY   (secret)  free tier at https://slickfast.com
#   CITY / LATITUDE / LONGITUDE / TIMEZONE / UNITS (vars) — your place; UNITS = metric|imperial
import json, os, sys, urllib.request, urllib.parse, uuid, datetime

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")   # not needed for `live` mode
TG = f"https://api.telegram.org/bot{TOKEN}"

# `or` (not .get defaults): GitHub Actions passes UNSET vars as empty strings,
# which must also fall back — a bare .get default would let '' through and crash.
CITY     = os.environ.get("CITY") or "Chicago"
LAT      = float(os.environ.get("LATITUDE") or "41.8781")
LON      = float(os.environ.get("LONGITUDE") or "-87.6298")
TIMEZONE = os.environ.get("TIMEZONE") or "America/Chicago"  # IANA name; also used for labels
UNITS    = (os.environ.get("UNITS") or "imperial").lower()  # metric (°C, km/h) | imperial (°F, mph)
IMPERIAL = UNITS == "imperial"
T_UNIT, W_UNIT = ("°F", " mph") if IMPERIAL else ("°C", " km/h")

def tg_get(method):
    with urllib.request.urlopen(f"{TG}/{method}", timeout=30) as r:
        return json.load(r)

def discover():
    me = tg_get("getMe").get("result", {})
    print(f"BOT USERNAME: @{me.get('username')}  → message this bot in Telegram, then re-run")
    ups = tg_get("getUpdates").get("result", [])
    if not ups:
        print("NO UPDATES — open Telegram, send the bot any message, re-run discover.")
        return
    for u in ups[-5:]:
        c = (u.get("message") or u.get("channel_post") or {}).get("chat", {})
        print(f"chat_id: {c.get('id')}  ({c.get('type')}, {c.get('first_name') or c.get('title')})")

def weather():
    q = urllib.parse.urlencode({
        "latitude": LAT, "longitude": LON, "timezone": TIMEZONE,
        **({"temperature_unit": "fahrenheit", "wind_speed_unit": "mph"} if IMPERIAL else {}),
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,precipitation",
        "hourly": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max",
        "forecast_days": 7,
    })
    with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{q}", timeout=30) as r:
        return json.load(r)

def air_quality():
    # Open-Meteo's air-quality API (same free/no-key deal, separate endpoint).
    # Fail-soft: if it's down, the dashboard just skips the AQI tile.
    q = urllib.parse.urlencode({"latitude": LAT, "longitude": LON, "timezone": TIMEZONE,
                                "current": "us_aqi"})
    try:
        with urllib.request.urlopen(f"https://air-quality-api.open-meteo.com/v1/air-quality?{q}", timeout=30) as r:
            return json.load(r)["current"]["us_aqi"]
    except Exception:
        return None

def aqi_color(aqi):
    # US EPA bands: green/yellow/orange/red/purple/maroon.
    for limit, color in [(50, "#22c55e"), (100, "#eab308"), (150, "#f97316"),
                         (200, "#ef4444"), (300, "#a855f7")]:
        if aqi <= limit:
            return color
    return "#7f1d1d"

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def local_now(w):
    # Open-Meteo returns the location's UTC offset — no tz database needed.
    off = datetime.timedelta(seconds=w.get("utc_offset_seconds", 0))
    return datetime.datetime.now(datetime.timezone.utc) + off

def next_hours(w, now, count=12, step=2):
    """Next `count` samples (every `step` h) of hourly temp, from the current hour."""
    t, temp = w["hourly"]["time"], w["hourly"]["temperature_2m"]
    cur = now.strftime("%Y-%m-%dT%H")
    start = next((i for i, ts in enumerate(t) if ts[:13] >= cur), 0)
    idx = list(range(start, min(start + count * step, len(t)), step))
    labels = [f"{(int(t[i][11:13]) % 12) or 12}{'a' if int(t[i][11:13]) < 12 else 'p'}" for i in idx]
    return labels, [round(temp[i]) for i in idx]

# The look: light mint theme. Tweak these four lines to restyle everything.
BG   = "#D7EAE1"   # canvas
TILE = "#EFF9F4"   # tile cards
GRN  = "#12B981"   # primary highlight
PINK = "#D63FBE"   # secondary highlight

def build_spec(w):
    cur, day = w["current"], w["daily"]
    days = [DAYS[datetime.date.fromisoformat(d).weekday()] for d in day["time"]]
    now = local_now(w)
    hlabels, htemps = next_hours(w, now)
    W1, W2 = 500, 1020   # 1-col slot width, 2-col (full) slot width
    # AQI (gauge, EPA-band color) + today's max UV — the "should I go outside" row.
    # Skipped as a pair if the air-quality API is unavailable, keeping the grid even.
    aqi = air_quality()
    aqi_tiles = [] if aqi is None else [
        {"chart": {"type": "gauge", "background": TILE, "width": W1, "height": 300,
                   "title": "air quality (US AQI)", "value": round(aqi), "max": 300,
                   "color": aqi_color(aqi)}},
        {"chart": {"type": "kpi", "background": TILE, "width": W1, "height": 300,
                   "label": "max UV index today", "value": round(day["uv_index_max"][0]),
                   "color": "#f59e0b" if day["uv_index_max"][0] >= 6 else GRN}},
    ]
    return {
        "type": "dashboard",
        "title": f"{CITY} · {now.strftime('%a · %b %-d · %-I:%M %p')}",
        "background": BG,
        "palette": "Vibrant",
        # Each tile's width/height = its slot size so the card color fills edge to edge.
        "layout": {"cols": 2, "gap": 20, "tileWidth": W1, "tileHeight": 300},
        "tiles": [
            {"chart": {"type": "kpi", "background": TILE, "width": W1, "height": 300,
                       "label": f"now · feels like {round(cur['apparent_temperature'])}°",
                       "value": round(cur["temperature_2m"]), "valueUnit": T_UNIT, "color": GRN}},
            {"chart": {"type": "gauge", "background": TILE, "width": W1, "height": 300,
                       "title": "chance of rain today",
                       "value": day["precipitation_probability_max"][0], "max": 100, "color": PINK}},
            {"chart": {"type": "kpi", "background": TILE, "width": W1, "height": 300,
                       "label": "wind", "value": round(cur["wind_speed_10m"]),
                       "valueUnit": W_UNIT, "color": GRN}},
            {"chart": {"type": "kpi", "background": TILE, "width": W1, "height": 300,
                       "label": "humidity", "value": round(cur["relative_humidity_2m"]),
                       "valueUnit": "%", "color": PINK}},
            *aqi_tiles,
            {"chart": {"type": "line", "background": TILE, "width": W2, "height": 300,
                       "title": f"hourly temperature ({T_UNIT})", "curve": "smooth", "area": True,
                       "data": {"labels": hlabels, "series": [
                           {"name": T_UNIT, "values": htemps, "color": GRN}]}},
             "span": [2, 1]},
            {"chart": {"type": "grouped", "background": TILE, "width": W2, "height": 300,
                       "title": f"next 7 days · high / low ({T_UNIT})",
                       "data": {"labels": days, "series": [
                           {"name": "high", "values": [round(v) for v in day["temperature_2m_max"]], "color": GRN},
                           {"name": "low", "values": [round(v) for v in day["temperature_2m_min"]], "color": PINK}]}},
             "span": [2, 1]},
        ],
    }

def render_png(spec):
    req = urllib.request.Request(
        "https://api.slickfast.com/render",
        data=json.dumps({**spec, "format": "png"}).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {os.environ['SLICKFAST_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def send_photo(png, chat_id):
    # Multipart upload — Telegram caches photos by URL, so we send BYTES (always fresh).
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"weather.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{TG}/sendPhoto", data=body,
                                 headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def publish_live(name):
    # Publish/refresh a LIVE chart: permanent URL, always shows the latest push.
    # A freshness stamp is appended to the title so viewers can SEE it's current.
    from zoneinfo import ZoneInfo
    spec = build_spec(weather())
    et = datetime.datetime.now(ZoneInfo("America/New_York"))
    spec["title"] += f"  ·  updated {et.strftime('%b %-d, %-I:%M %p')} ET"
    req = urllib.request.Request(
        f"https://api.slickfast.com/live/{name}",
        data=json.dumps(spec).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {os.environ['SLICKFAST_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.load(r)
    print("live chart updated:")
    print("  SVG:", out.get("svg"))
    print("  PNG:", out.get("png"))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "send"
    if mode == "discover":
        discover()
    elif mode == "live":
        publish_live(sys.argv[2] if len(sys.argv) > 2 else "my-weather")
    else:
        png = render_png(build_spec(weather()))
        out = send_photo(png, os.environ["TELEGRAM_CHAT_ID"])
        print("sent:", out.get("ok"), f"({len(png)//1024} KB)")
