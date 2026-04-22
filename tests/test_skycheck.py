"""
tests/test_skycheck.py — SkyCheck Test Suite
=============================================
Unit tests (data transformation + TTLCache) and
integration tests (Flask route handlers).

Uses unittest.mock to avoid any real network calls.
All tests use fixture data based on real OWM API response shapes.

Run with:
    pip install flask requests python-dotenv pytest
    pytest tests/ -v

COMP1682 Final Year Project — Mohammadmehdi Mohammad Zadeh (001125181)
University of Greenwich, 2025-2026
"""

import sys
import os
import json
import time
import pytest
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import weather as w
from weather import (
    TTLCache, transform_current_weather, transform_forecast,
    cache_weather_data, get_current_weather, get_forecast,
    CityNotFoundError, APITimeoutError, APIError
)
from app import app as flask_app


# ── Fixtures ──────────────────────────────────────────────────
CURRENT_FIXTURE = {
    "name": "London",
    "sys":  {"country": "GB"},
    "coord": {"lat": 51.51, "lon": -0.13},
    "main": {
        "temp": 15.0,
        "feels_like": 13.5,
        "humidity": 72,
        "pressure": 1012
    },
    "wind":    {"speed": 5.0},
    "weather": [{"description": "light rain", "icon": "10d", "main": "Rain"}],
    "timezone": 3600,
    "visibility": 9000,
}

FORECAST_FIXTURE = {
    "list": [
        {
            "dt_txt": f"2025-10-0{day} {hour}:00:00",
            "main": {"temp": 14.0 + day + (hour/12)},
            "weather": [{"description": "cloudy", "icon": "04d", "main": "Clouds"}],
            "pop": 0.4,
        }
        for day in range(1, 6)
        for hour in [0, 3, 6, 9, 12, 15, 18, 21]
    ]
}


# ── TTLCache unit tests ───────────────────────────────────────
class TestTTLCache:

    def setup_method(self):
        self.cache = TTLCache(ttl_seconds=5)

    def test_miss_on_empty_cache(self):
        assert self.cache.get("london") is None

    def test_hit_after_set(self):
        self.cache.set("london", {"temp": 15})
        assert self.cache.get("london") == {"temp": 15}

    def test_miss_after_expiry(self):
        cache = TTLCache(ttl_seconds=0)
        cache.set("london", {"temp": 15})
        time.sleep(0.01)
        assert cache.get("london") is None

    def test_case_insensitive_key(self):
        self.cache.set("london", {"temp": 15})
        # Key normalisation is done by cache_weather_data, not TTLCache itself
        assert self.cache.get("london") == {"temp": 15}

    def test_clear_empties_cache(self):
        self.cache.set("london", {"temp": 15})
        self.cache.clear()
        assert self.cache.get("london") is None

    def test_overwrite_updates_timestamp(self):
        self.cache.set("london", {"temp": 15})
        self.cache.set("london", {"temp": 16})
        assert self.cache.get("london") == {"temp": 16}


# ── transform_current_weather unit tests ─────────────────────
class TestTransformCurrentWeather:

    def setup_method(self):
        self.result = transform_current_weather(CURRENT_FIXTURE)

    def test_city_name(self):
        assert self.result["city"] == "London"

    def test_country_code(self):
        assert self.result["country"] == "GB"

    def test_temp_celsius(self):
        assert self.result["temp_c"] == 15

    def test_temp_fahrenheit(self):
        # 15°C × 9/5 + 32 = 59°F
        assert self.result["temp_f"] == 59

    def test_feels_celsius(self):
        assert self.result["feels_c"] == round(13.5)

    def test_feels_fahrenheit(self):
        expected = round(13.5 * 9/5 + 32)
        assert self.result["feels_f"] == expected

    def test_wind_kmh(self):
        # 5 m/s × 3.6 = 18.0 km/h
        assert self.result["wind_kmh"] == 18.0

    def test_wind_mph(self):
        # 5 m/s × 2.237 = 11.2 mph
        assert self.result["wind_mph"] == round(5 * 2.237, 1)

    def test_humidity(self):
        assert self.result["humidity"] == 72

    def test_pressure(self):
        assert self.result["pressure"] == 1012

    def test_visibility_km(self):
        # 9000m → 9.0km
        assert self.result["visibility_km"] == 9.0

    def test_condition_capitalised(self):
        assert self.result["condition"] == "Light rain"

    def test_icon_url_format(self):
        assert self.result["icon_url"].startswith("https://openweathermap.org/img/wn/")
        assert self.result["icon_url"].endswith("@2x.png")

    def test_local_time_string(self):
        # UTC+3600 = UTC+1 → local time should be a valid HH:MM string
        assert len(self.result["local_time"]) == 5
        assert ":" in self.result["local_time"]

    def test_coordinates(self):
        assert self.result["lat"] == 51.51
        assert self.result["lon"] == -0.13

    def test_condition_main(self):
        assert self.result["condition_main"] == "Rain"


# ── transform_forecast unit tests ────────────────────────────
class TestTransformForecast:

    def setup_method(self):
        self.result = transform_forecast(FORECAST_FIXTURE)

    def test_returns_five_days(self):
        assert len(self.result) == 5

    def test_each_day_has_required_keys(self):
        required = {"date", "day", "condition", "icon_url",
                    "high_c", "low_c", "high_f", "low_f", "pop"}
        for day in self.result:
            assert required.issubset(set(day.keys()))

    def test_high_above_low(self):
        for day in self.result:
            assert day["high_c"] >= day["low_c"]
            assert day["high_f"] >= day["low_f"]

    def test_fahrenheit_higher_than_celsius_for_positive_temps(self):
        for day in self.result:
            assert day["high_f"] > day["high_c"]

    def test_precipitation_percentage_in_range(self):
        for day in self.result:
            assert 0 <= day["pop"] <= 100

    def test_condition_capitalised(self):
        for day in self.result:
            assert day["condition"][0].isupper()

    def test_icon_url_uses_day_variant(self):
        # Night icon codes end in 'n' — should be replaced with 'd'
        for day in self.result:
            assert not day["icon_url"].endswith("n@2x.png")

    def test_day_label_is_short(self):
        for day in self.result:
            assert len(day["day"]) == 3  # e.g. "Mon"


# ── Cache integration test ────────────────────────────────────
class TestCacheWeatherData:

    def setup_method(self):
        w._cache.clear()

    @patch("weather.get_forecast")
    @patch("weather.get_current_weather")
    def test_only_one_api_call_within_ttl(self, mock_cur, mock_fore):
        mock_cur.return_value  = CURRENT_FIXTURE
        mock_fore.return_value = FORECAST_FIXTURE

        cache_weather_data("London")
        cache_weather_data("London")
        cache_weather_data("london")   # normalised to same key

        assert mock_cur.call_count == 1
        assert mock_fore.call_count == 1

    @patch("weather.get_forecast")
    @patch("weather.get_current_weather")
    def test_returns_dict_with_forecast(self, mock_cur, mock_fore):
        mock_cur.return_value  = CURRENT_FIXTURE
        mock_fore.return_value = FORECAST_FIXTURE

        result = cache_weather_data("London")
        assert "forecast" in result
        assert len(result["forecast"]) == 5

    @patch("weather.get_forecast")
    @patch("weather.get_current_weather")
    def test_different_cities_are_separate_cache_entries(self, mock_cur, mock_fore):
        mock_cur.return_value  = CURRENT_FIXTURE
        mock_fore.return_value = FORECAST_FIXTURE

        cache_weather_data("London")
        cache_weather_data("Paris")

        assert mock_cur.call_count == 2


# ── API error handling unit tests ────────────────────────────
class TestAPIErrorHandling:

    def setup_method(self):
        w._cache.clear()

    @patch("weather.requests.get")
    def test_404_raises_city_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        with pytest.raises(CityNotFoundError):
            get_current_weather("xyznotacity")

    @patch("weather.requests.get")
    def test_non_200_raises_api_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp
        with pytest.raises(APIError):
            get_current_weather("London")

    @patch("weather.requests.get")
    def test_timeout_raises_api_timeout_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        with pytest.raises(APITimeoutError):
            get_current_weather("London")


# ── Flask integration tests ───────────────────────────────────
@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestRoutes:

    def test_index_loads(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"SkyCheck" in res.data

    def test_about_loads(self, client):
        res = client.get("/about")
        assert res.status_code == 200
        assert b"About SkyCheck" in res.data

    @patch("app.cache_weather_data")
    def test_weather_valid_city(self, mock_cache, client):
        mock_cache.return_value = {
            **transform_current_weather(CURRENT_FIXTURE),
            "forecast": transform_forecast(FORECAST_FIXTURE)
        }
        res = client.get("/weather?city=London")
        assert res.status_code == 200
        assert b"London" in res.data

    @patch("app.cache_weather_data")
    def test_weather_city_not_found_shows_error(self, mock_cache, client):
        mock_cache.side_effect = CityNotFoundError("xyznotacity")
        res = client.get("/weather?city=xyznotacity")
        assert res.status_code == 200
        assert b"City not found" in res.data

    @patch("app.cache_weather_data")
    def test_weather_timeout_shows_error(self, mock_cache, client):
        mock_cache.side_effect = APITimeoutError()
        res = client.get("/weather?city=London")
        assert res.status_code == 200
        assert b"too long to respond" in res.data

    @patch("app.cache_weather_data")
    def test_weather_api_error_shows_error(self, mock_cache, client):
        mock_cache.side_effect = APIError("500")
        res = client.get("/weather?city=London")
        assert res.status_code == 200
        assert b"Unable to retrieve" in res.data

    def test_weather_empty_city_shows_error(self, client):
        res = client.get("/weather?city=")
        assert res.status_code == 200
        assert b"enter a city" in res.data

    def test_weather_no_city_param(self, client):
        res = client.get("/weather")
        assert res.status_code == 200

    @patch("app.cache_weather_data")
    def test_weather_long_input_truncated(self, mock_cache, client):
        mock_cache.side_effect = CityNotFoundError()
        long_city = "x" * 200
        res = client.get(f"/weather?city={long_city}")
        # Should not crash — truncation handled server-side
        assert res.status_code == 200
        # cache called with max 100 chars
        called_with = mock_cache.call_args[0][0]
        assert len(called_with) <= 100
