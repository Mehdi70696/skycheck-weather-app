# SkyCheck — Real-Time Weather Application
## COMP1682 Final Year Project
**Student:** Mohammadmehdi Mohammad Zadeh | **Banner ID:** 001125181
**University of Greenwich** | BSc (Hons) Computer Science | 2025–2026

---

## How to Run This Project

### What You Need First
- **Python** (version 3.10 or higher) — download from [python.org](https://www.python.org/downloads/)
  - During installation on Windows, tick **"Add Python to PATH"**
- **An OpenWeatherMap API key** (free) — instructions below

---

### Step 1 — Get a Free API Key

1. Go to **https://openweathermap.org/**
2. Click **Sign In** → **Create an Account** (it is free)
3. After signing in, go to **API Keys** in your account menu
4. Copy your API key (it looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)

> **Note:** New API keys can take up to 2 hours to activate. If you get an "Invalid API key" error on the page, please wait a short while and try again.

---

### Step 2 — Download the Code

**From GitHub:**
1. Go to **https://github.com/mehdi70696/skycheck-weather-app**
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Unzip the downloaded file and open the `skycheck` folder

---

### Step 3 — Set Up the API Key

1. Inside the `skycheck` folder, find the file called **`.env.example`**
2. Make a copy of it and rename the copy to **`.env`**
3. Open `.env` with any text editor (Notepad on Windows, TextEdit on Mac)
4. Replace `your_openweathermap_api_key_here` with your real API key:

```
OWM_API_KEY=paste_your_key_here
```

---

### Step 4 — Install Dependencies

Open a **terminal** (or Command Prompt on Windows) inside the `skycheck` folder and run:

```
pip install flask requests python-dotenv
```

---

### Step 5 — Run the Application

In the same terminal, run:

```
python app.py
```

You should see:

```
INFO  SkyCheck starting on http://localhost:5000
```

---

### Step 6 — Open in Browser

Open your web browser and go to:

```
http://localhost:5000
```

Type any city name (e.g. **London**, **New York**, **Tokyo**) and press Search.

---

### Step 7 — Run the Tests (Optional)

To run the automated test suite:

```
pip install pytest
pytest tests/ -v
```

All 45 tests should pass. The tests use mock data so no API key is needed.

---

## Project Structure

```
skycheck/
├── app.py                  Flask application (3 routes: /, /weather, /about)
├── weather.py              API integration, TTLCache, data transformation
├── requirements.txt        Python dependencies
├── .env.example            API key template (copy to .env and add your key)
├── .gitignore              Excludes .env from version control
├── README.md               This file
├── templates/
│   ├── base.html           Shared page layout (navbar, footer)
│   ├── index.html          Homepage with city search form
│   ├── weather.html        Weather results and 5-day forecast
│   └── about.html          About page
├── static/
│   ├── css/style.css       All styling (responsive, dynamic backgrounds)
│   └── js/toggle.js        Celsius/Fahrenheit toggle
└── tests/
    └── test_skycheck.py    45 unit and integration tests
```

---

## What the Application Does

- Search any city in the world and get live weather data
- Displays temperature, feels-like, humidity, wind speed, pressure, visibility
- 5-day forecast with daily high/low temperatures and precipitation probability
- Toggle between Celsius and Fahrenheit instantly without reloading the page
- Dynamic background colour changes based on weather conditions
- Graceful error handling for invalid cities, timeouts, and network failures
- Server-side cache stores responses for 5 minutes to reduce API calls

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install flask requests python-dotenv` |
| "Invalid API key" shown on page | Wait up to 2 hours after creating your OWM account |
| `OWM_API_KEY environment variable is not set` | Make sure you created `.env` (not `.env.example`) with your key inside |
| Port already in use | Change the port in app.py last line to `app.run(port=5001)` |
| Cannot find `.env` file | Enable "Show hidden files" in your file explorer — it may be hidden |
