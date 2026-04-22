"""
weather.py — SkyCheck Weather Module
======================================
Handles:
  - OpenWeatherMap API calls (current weather + 5-day forecast)
  - Data transformation (unit conversion, timestamp formatting)
  - TTLCache (5-minute server-side response cache)
  - Custom exceptions (CityNotFoundError, APITimeoutError, APIError)

COMP1682 Final Year Project — Mohammadmehdi Mohammad Zadeh (001125181)
University of Greenwich, 2025-2026
"""

import os
import time
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict


# ── Custom exceptions ─────────────────────────────────────────
class CityNotFoundError(Exception):
    """Raised when the API returns 404 for an unknown city."""
    pass


class APITimeoutError(Exception):
    """Raised when the API request exceeds the timeout threshold."""
    pass


class APIError(Exception):
    """Raised for any other non-200 API response."""
    pass


# ── TTL Cache ─────────────────────────────────────────────────
class TTLCache:
    """
    Simple in-memory time-to-live cache.
    Each entry is stored as (value, timestamp). Entries older than
    ttl_seconds are treated as expired and re-fetched from the API.
    """

    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self.ttl = ttl_seconds

    def get(self, key):
        """Return cached value if it exists and is within TTL, else None."""
        if key in self._cache:
            value, ts = self._cache[key]
            if time.time() - ts < self.ttl:
                return value
        return None

    def set(self, key, value):
        """Store a value with the current timestamp."""
        self._cache[key] = (value, time.time())

    def clear(self):
        """Clear all cached entries (used in tests)."""
        self._cache.clear()


_cache = TTLCache(ttl_seconds=300)

API_BASE    = "https://api.openweathermap.org/data/2.5"
API_TIMEOUT = 10  # seconds


# ── Public cache wrapper ──────────────────────────────────────
def cache_weather_data(city: str) -> dict:
    """
    Return weather data for the given city, using the cache if available.
    City names are normalised to lowercase with whitespace stripped to
    prevent case-sensitive cache misses.
    """
    key = city.strip().lower()
    cached = _cache.get(key)
    if cached:
        return cached

    current  = get_current_weather(key)
    forecast = get_forecast(key)
    data = {
        **transform_current_weather(current),
        "forecast": transform_forecast(forecast),
    }
    _cache.set(key, data)
    return data


# ── API calls ─────────────────────────────────────────────────
def _api_key() -> str:
    """Return the OpenWeatherMap API key from the environment."""
    key = os.environ.get("OWM_API_KEY", "")
    if not key:
        raise APIError("OWM_API_KEY environment variable is not set.")
    return key


def get_current_weather(city: str) -> dict:
    """
    Fetch current weather for a city from the OpenWeatherMap API.
    Raises CityNotFoundError, APITimeoutError, or APIError as appropriate.
    """
    url = f"{API_BASE}/weather"
    params = {"q": city, "appid": _api_key(), "units": "metric"}
    try:
        resp = requests.get(url, params=params, timeout=API_TIMEOUT)
    except requests.exceptions.Timeout:
        raise APITimeoutError(f"Timeout fetching current weather for {city!r}")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error: {e}")

    if resp.status_code == 404:
        raise CityNotFoundError(f"City not found: {city!r}")
    if resp.status_code != 200:
        raise APIError(f"API returned {resp.status_code} for {city!r}")

    return resp.json()


def get_forecast(city: str) -> dict:
    """
    Fetch 5-day / 3-hourly forecast for a city (40 data points).
    Raises CityNotFoundError, APITimeoutError, or APIError as appropriate.
    """
    url = f"{API_BASE}/forecast"
    params = {"q": city, "appid": _api_key(), "units": "metric"}
    try:
        resp = requests.get(url, params=params, timeout=API_TIMEOUT)
    except requests.exceptions.Timeout:
        raise APITimeoutError(f"Timeout fetching forecast for {city!r}")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error: {e}")

    if resp.status_code == 404:
        raise CityNotFoundError(f"City not found: {city!r}")
    if resp.status_code != 200:
        raise APIError(f"API returned {resp.status_code} for {city!r}")

    return resp.json()


# ── Data transformation ───────────────────────────────────────
def transform_current_weather(data: dict) -> dict:
    """
    Transform raw OpenWeatherMap current-weather JSON into a clean dict
    ready for the Jinja2 template.

    Key transformations:
      - Temperature stored in both Celsius and Fahrenheit
      - Wind speed converted from m/s to km/h and mph
      - Unix timestamp + UTC offset → local time string
      - Pressure in hPa, visibility in km
    """
    # Temperatures (API returns Celsius when units=metric)
    temp_c       = round(data["main"]["temp"])
    feels_c      = round(data["main"]["feels_like"])
    temp_f       = round(temp_c * 9/5 + 32)
    feels_f      = round(feels_c * 9/5 + 32)

    # Wind speed: m/s → km/h and mph
    wind_ms      = data.get("wind", {}).get("speed", 0)
    wind_kmh     = round(wind_ms * 3.6, 1)
    wind_mph     = round(wind_ms * 2.237, 1)

    # Local time using UTC offset from API
    utc_offset   = data.get("timezone", 0)           # seconds east of UTC
    utc_now      = datetime.utcnow().replace(tzinfo=timezone.utc)
    local_time   = utc_now + timedelta(seconds=utc_offset)
    local_str    = local_time.strftime("%H:%M")
    local_date   = local_time.strftime("%A, %d %B %Y")

    # Visibility: API returns metres, convert to km
    visibility_m = data.get("visibility", 0)
    visibility_km = round(visibility_m / 1000, 1)

    # Weather condition
    condition    = data["weather"][0]["description"].capitalize()
    icon_code    = data["weather"][0]["icon"]
    icon_url     = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
    condition_main = data["weather"][0]["main"]   # e.g. 'Clear', 'Rain'

    # Coordinates
    lat = round(data["coord"]["lat"], 2)
    lon = round(data["coord"]["lon"], 2)

    return {
        "city":          data["name"],
        "country":       data["sys"]["country"],
        "lat":           lat,
        "lon":           lon,
        "temp_c":        temp_c,
        "temp_f":        temp_f,
        "feels_c":       feels_c,
        "feels_f":       feels_f,
        "humidity":      data["main"]["humidity"],
        "pressure":      data["main"]["pressure"],
        "wind_kmh":      wind_kmh,
        "wind_mph":      wind_mph,
        "visibility_km": visibility_km,
        "condition":     condition,
        "condition_main": condition_main,
        "icon_url":      icon_url,
        "local_time":    local_str,
        "local_date":    local_date,
    }


def transform_forecast(data: dict) -> list:
    """
    Transform raw 5-day / 3-hourly forecast (40 objects) into a list of
    5 daily summary dicts. Each daily summary picks the midday reading
    (or closest available) as the representative condition, and records
    the day's high and low temperatures.
    """
    # Group readings by date
    by_date = defaultdict(list)
    for item in data["list"]:
        date_str = item["dt_txt"].split(" ")[0]   # "YYYY-MM-DD"
        by_date[date_str].append(item)

    daily = []
    for date_str in sorted(by_date.keys())[:5]:
        readings = by_date[date_str]

        # Pick midday reading (12:00 if available, else closest to noon)
        midday = min(readings, key=lambda r: abs(
            int(r["dt_txt"].split(" ")[1].split(":")[0]) - 12
        ))

        temps    = [r["main"]["temp"] for r in readings]
        high_c   = round(max(temps))
        low_c    = round(min(temps))
        high_f   = round(high_c * 9/5 + 32)
        low_f    = round(low_c  * 9/5 + 32)

        icon_code = midday["weather"][0]["icon"]
        # Use day icon variant
        icon_code = icon_code.replace("n", "d")

        # Format day label
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_label = dt.strftime("%a")   # e.g. "Mon"

        # Precipitation probability (0–1, convert to %)
        pop = round(midday.get("pop", 0) * 100)

        daily.append({
            "date":      date_str,
            "day":       day_label,
            "condition": midday["weather"][0]["description"].capitalize(),
            "icon_url":  f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
            "high_c":    high_c,
            "low_c":     low_c,
            "high_f":    high_f,
            "low_f":     low_f,
            "pop":       pop,
        })

    return daily
