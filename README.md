# 🌧️ RainCheck AI (Streamlit)

A modern Streamlit web application that detects whether rain is currently falling or forecasted to fall at any location and time, powered by **Google's WeatherNext 3** (via Google Maps Platform Weather API).

---

## ✨ Features

- **Real-Time Rain Status Detection:** Instantly answers *"Is it raining right now?"* with a vibrant status badge, rain rate (mm/h or in/h), probability percentage, and weather condition.
- **Smart Defaults:**
  - **Location:** Auto-detects current location via IP geolocation on launch.
  - **Time:** Defaults to the current moment (`now`), with support for custom forecast dates and times.
- **Google WeatherNext 3 Integration:** Connects directly to Google's high-resolution (5km) AI weather foundation model via `weather.googleapis.com`.
- **Zero-Friction Fallback:** Fully operational right out of the box with an automatic fallback simulation engine if no Google API key is provided yet.
- **24-Hour Precipitation Timeline:** Interactive bar charts showing rain probability and accumulated rainfall volume hour by hour.
- **Interactive Map:** Shows the exact coordinates and geographic context of the queried location.
- **Quick City Presets:** Easily toggle between current location, Bangkok, Tokyo, Singapore, London, Seattle, New York, etc.

---

## 🚀 How to Run

### 1. Activate Virtual Environment
```powershell
.venv\Scripts\activate
```

### 2. Run the Streamlit App
```powershell
.venv\Scripts\streamlit run app.py
```
Or with custom port:
```powershell
.venv\Scripts\streamlit run app.py --server.port 8501
```

---

## 🔑 WeatherNext 3 API Configuration

Google's **WeatherNext 3** model powers the Google Maps Platform Weather API (`weather.googleapis.com`).

You can configure your API key in two ways:
1. **Directly in the App:** Enter your API key in the sidebar under **"Google Maps / Weather API Key"**.
2. **Via `.env` file:** Copy `.env.example` to `.env` and set:
   ```env
   GOOGLE_MAPS_API_KEY=your_key_here
   ```
