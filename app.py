"""
app.py — SkyCheck Application Entry Point
==========================================
Three routes: / (index), /weather, /about

Run with:
    pip install flask requests python-dotenv
    python app.py
    Open http://localhost:5000

COMP1682 Final Year Project — Mohammadmehdi Mohammad Zadeh (001125181)
University of Greenwich, 2025-2026
"""

from flask import Flask, render_template, request
from weather import cache_weather_data, CityNotFoundError, APITimeoutError, APIError
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    """Render the homepage with empty search field."""
    return render_template("index.html")


@app.route("/weather")
def weather():
    """
    Accept a city query parameter, fetch weather data (via cache),
    and render the weather template. Handles all error conditions
    gracefully with user-friendly messages.
    """
    city = request.args.get("city", "").strip()

    # Client-side JS handles empty input, but guard server-side too
    if not city:
        return render_template("index.html", error="Please enter a city name.")

    # Truncate very long inputs server-side
    if len(city) > 100:
        city = city[:100]

    try:
        data = cache_weather_data(city)
        return render_template("weather.html", weather=data, city=city)

    except CityNotFoundError:
        log.info(f"City not found: {city!r}")
        return render_template("weather.html",
                               error="City not found. Please check the spelling and try again.",
                               city=city)

    except APITimeoutError:
        log.warning(f"API timeout for city: {city!r}")
        return render_template("weather.html",
                               error="The weather service is taking too long to respond. "
                                     "Please try again in a moment.",
                               city=city)

    except APIError as e:
        log.error(f"API error for city {city!r}: {e}")
        return render_template("weather.html",
                               error="Unable to retrieve weather data. Please try again later.",
                               city=city)


@app.route("/about")
def about():
    """Render the about page describing the application and data sources."""
    return render_template("about.html")


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    log.info("SkyCheck starting on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
