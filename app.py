import os
from datetime import datetime, date, time, timedelta
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

from weathernext_service import WeatherNextService

# Page Configuration
st.set_page_config(
    page_title="RainCheck — Google WeatherNext 3",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern weather dashboard aesthetics
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        color: #1E293B;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .status-card-rain {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.4);
        margin-bottom: 20px;
    }
    .status-card-norain {
        background: linear-gradient(135deg, #065f46 0%, #10b981 100%);
        color: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.4);
        margin-bottom: 20px;
    }
    .status-card-warning {
        background: linear-gradient(135deg, #9a3412 0%, #f97316 100%);
        color: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(249, 115, 22, 0.4);
        margin-bottom: 20px;
    }
    .card-headline {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .card-detail {
        font-size: 1.1rem;
        opacity: 0.95;
    }
    .metric-container {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "detected_loc" not in st.session_state:
    with st.spinner("Detecting your current location..."):
        st.session_state.detected_loc = WeatherNextService.detect_current_location()

detected = st.session_state.detected_loc

if "selected_location_name" not in st.session_state:
    st.session_state.selected_location_name = detected["name"]

if "loc_text_input" not in st.session_state:
    st.session_state["loc_text_input"] = detected["name"]

if "selected_lat" not in st.session_state:
    st.session_state.selected_lat = detected["latitude"]

if "selected_lon" not in st.session_state:
    st.session_state.selected_lon = detected["longitude"]

# Location management callbacks
def set_location(lat: float, lon: float, name: str):
    st.session_state.selected_lat = lat
    st.session_state.selected_lon = lon
    st.session_state.selected_location_name = name
    st.session_state["loc_text_input"] = name
    st.session_state.pop("search_error", None)

def reset_to_current_location():
    fresh = WeatherNextService.detect_current_location()
    st.session_state.detected_loc = fresh
    set_location(fresh["latitude"], fresh["longitude"], fresh["name"])

def search_location():
    query = st.session_state.get("loc_text_input", "").strip()
    if query:
        geo_res = WeatherNextService.geocode_location(query, st.session_state.get("google_api_key"))
        if geo_res:
            glat, glon, gname = geo_res
            set_location(glat, glon, gname)
        else:
            st.session_state["search_error"] = f"Could not locate '{query}'. Please check the spelling or enter coordinates."

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ WeatherNext 3 Settings")

    # Load API key silently from .env, environment variables, or st.secrets
    env_google_key = os.getenv("GOOGLE_WEATHER_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not env_google_key:
        try:
            env_google_key = st.secrets.get("GOOGLE_WEATHER_API_KEY") or st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        except Exception:
            pass
    
    st.session_state.google_api_key = (env_google_key or "").strip()

    if st.session_state.google_api_key:
        st.success("🟢 Google WeatherNext 3 Live Model Active")
    else:
        st.info("ℹ️ Using Fallback Simulation Mode (Configure key in `.env` to activate live WeatherNext 3)")

    units = st.selectbox("Units System", ["METRIC (°C, mm)", "IMPERIAL (°F, in)"], index=0)
    units_code = "METRIC" if "METRIC" in units else "IMPERIAL"

    st.divider()

    st.markdown("### 📍 Quick City Selector")
    popular_cities = {
        "📍 My Current Location": (detected["latitude"], detected["longitude"], detected["name"]),
        "Bangkok": (13.7563, 100.5018, "Bangkok, Thailand"),
        "Tokyo": (35.6762, 139.6503, "Tokyo, Japan"),
        "Singapore": (1.3521, 103.8198, "Singapore"),
        "London": (51.5074, -0.1278, "London, United Kingdom"),
        "Seattle": (47.6062, -122.3321, "Seattle, WA, USA"),
        "New York": (40.7128, -74.0060, "New York, NY, USA")
    }

    for city_name, (clat, clon, cdisplay) in popular_cities.items():
        if city_name == "📍 My Current Location":
            st.button(city_name, on_click=reset_to_current_location, use_container_width=True)
        else:
            st.button(city_name, on_click=set_location, args=(clat, clon, cdisplay), use_container_width=True)

    st.divider()
    st.markdown("""
    **About Google WeatherNext 3:**
    - Developed by **Google DeepMind & Google Research**
    - High resolution: **5x5 km grid**
    - Direct assimilation of real-time geostationary satellite data
    - Hourly forecasts & rapid updates
    """)

# Main Page Header
st.markdown('<div class="main-title">🌧️ RainCheck AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Real-time rain detection & forecasting powered by <strong>Google DeepMind WeatherNext 3</strong></div>',
    unsafe_allow_html=True
)

# Input Section: Location and Time
st.markdown("#### 1. Input Parameters")

col_loc, col_time = st.columns([1.2, 1.0])

with col_loc:
    st.markdown("**Location Input** (Default: Current Location)")
    loc_input = st.text_input(
        "Enter City, Address, or 'lat, lon'",
        key="loc_text_input",
        on_change=search_location,
        help="Type any city or address and press Enter, or click 'Search Location'."
    )

    if "search_error" in st.session_state:
        st.error(st.session_state["search_error"])

    btn_sub_col1, btn_sub_col2 = st.columns([1, 1])
    with btn_sub_col1:
        st.button("📍 Reset to Current Location", on_click=reset_to_current_location, use_container_width=True)
    with btn_sub_col2:
        st.button("🔎 Search Location", on_click=search_location, use_container_width=True)

with col_time:
    st.markdown("**Time Input** (Default: Right Now)")
    time_mode = st.radio(
        "Select Time Mode",
        ["⚡ Right Now (Real-time)", "📅 Specific Time (Forecast)"],
        horizontal=True
    )

    target_dt = None
    if time_mode == "📅 Specific Time (Forecast)":
        now_dt = datetime.now()
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            sel_date = st.date_input("Date", value=now_dt.date())
        with t_col2:
            sel_time = st.time_input("Time", value=now_dt.time())
        target_dt = datetime.combine(sel_date, sel_time)
        delta_hours = (target_dt - now_dt).total_seconds() / 3600.0
        if delta_hours > 0:
            st.caption(f"Target is **{delta_hours:.1f} hours** into the future.")
        elif delta_hours < -0.1:
            st.caption(f"Target is **{abs(delta_hours):.1f} hours** in the past.")
        else:
            st.caption("Target is approximately current time.")
    else:
        st.caption(f"Checking immediate live weather at: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Thailand Time / ICT, UTC+7)**")

st.divider()

# Fetch Weather Data
with st.spinner("Querying Google WeatherNext 3 model data..."):
    weather_info = WeatherNextService.get_weather_data(
        lat=st.session_state.selected_lat,
        lon=st.session_state.selected_lon,
        target_time=target_dt,
        google_api_key=st.session_state.google_api_key if st.session_state.google_api_key else None,
        units=units_code
    )

tz_display = f"{weather_info.get('timezone', 'Asia/Bangkok')} ({weather_info.get('utc_offset', 'UTC+7')})"

# Coordinate Confirmation and Query Badges
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    st.info(f"📌 **Target:** {st.session_state.selected_location_name}")
with c2:
    st.info(f"🌐 **Coordinates:** `{st.session_state.selected_lat:.4f}, {st.session_state.selected_lon:.4f}`")
with c3:
    time_label = "Right Now (Live)" if target_dt is None else target_dt.strftime("%Y-%m-%d %H:%M")
    st.info(f"⏰ **Time:** {time_label} • `{tz_display}`")

# Extract Core Findings
is_raining = weather_info["is_raining"]
precip_rate = weather_info["precipitation_rate"]
precip_prob = weather_info["precipitation_prob"]
precip_unit = weather_info["precipitation_unit"]
cond_text = weather_info["condition_text"]
temp_deg = weather_info["temperature"]
temp_unit = weather_info["temperature_unit"]
humidity = weather_info["humidity"]
source_name = weather_info["source"]
icon_url = weather_info.get("icon_url", "")

# Rain Result Hero Card
st.markdown("#### 2. Rain Status Result")

# Check if rain is expected soon if not currently raining
timeline = weather_info.get("timeline", [])
rain_expected_soon = False
next_rain_time = None
next_rain_prob = 0
if not is_raining and timeline and target_dt is None:
    for item in timeline[:6]:
        if item.get("rain_prob", 0) >= 50 or item.get("precipitation", 0) > 0.1:
            rain_expected_soon = True
            next_rain_time = item["time"]
            next_rain_prob = item["rain_prob"]
            break

time_context_title = "actively detected" if target_dt is None else f"forecasted at {weather_info.get('target_time_label', time_label)}"
card_headline_rain = "🌧️ YES, IT IS RAINING!" if target_dt is None else f"🌧️ YES, RAIN FORECASTED AT {weather_info.get('target_time_label', time_label)}!"
card_headline_norain = "☀️ NO, IT IS NOT RAINING" if target_dt is None else f"☀️ NO RAIN FORECASTED AT {weather_info.get('target_time_label', time_label)}"

if is_raining:
    st.markdown(f"""
    <div class="status-card-rain">
        <div class="card-headline">{card_headline_rain}</div>
        <div class="card-detail">
            Rain is {time_context_title} at <strong>{st.session_state.selected_location_name}</strong>.<br>
            Expected precipitation: <strong>{precip_rate} {precip_unit}/h</strong> | Probability: <strong>{precip_prob}%</strong> | Condition: <strong>{cond_text}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif rain_expected_soon:
    st.markdown(f"""
    <div class="status-card-warning">
        <div class="card-headline">🌦️ NO RAIN RIGHT NOW, BUT RAIN EXPECTED SOON!</div>
        <div class="card-detail">
            It is not raining right now, but WeatherNext 3 predicts rain around <strong>{next_rain_time}</strong> with a <strong>{next_rain_prob}%</strong> chance.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="status-card-norain">
        <div class="card-headline">{card_headline_norain}</div>
        <div class="card-detail">
            No rain {time_context_title} at <strong>{st.session_state.selected_location_name}</strong>.<br>
            Conditions are <strong>{cond_text}</strong> with <strong>{precip_prob}%</strong> chance of precipitation.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Metrics Grid
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(
        label="Precipitation Intensity",
        value=f"{precip_rate} {precip_unit}/h",
        delta="Rain Active" if is_raining else "Dry / Clear",
        delta_color="normal" if is_raining else "off"
    )
with m2:
    st.metric(
        label="Rain Probability",
        value=f"{precip_prob}%",
        delta=f"Condition: {cond_text}"
    )
with m3:
    st.metric(
        label="Temperature",
        value=f"{temp_deg} {temp_unit}",
        delta=f"Humidity: {humidity}%"
    )
with m4:
    st.metric(
        label="AI Forecasting Model",
        value="WeatherNext 3",
        delta="Google DeepMind" if weather_info["is_google_api"] else "Fallback active"
    )

# 24-Hour Forecast Timeline
if timeline:
    st.markdown("#### 3. 24-Hour Precipitation Timeline")
    df_timeline = pd.DataFrame(timeline)
    
    # Clean time labels for charting
    def format_time_label(t):
        try:
            if "T" in t:
                parts = t.split("T")[1][:5]
                return parts
            return t
        except Exception:
            return t

    df_timeline["Hour"] = df_timeline["time"].apply(format_time_label)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**Rain Probability (%) across Next 24 Hours**")
        st.bar_chart(df_timeline.set_index("Hour")["rain_prob"], color="#3b82f6")
    with chart_col2:
        st.markdown(f"**Precipitation Amount ({precip_unit}) across Next 24 Hours**")
        st.bar_chart(df_timeline.set_index("Hour")["precipitation"], color="#0284c7")

# Location Map & Model Details
st.markdown("#### 4. Location & Geographic Context")
map_col, info_col = st.columns([1.2, 1.0])

with map_col:
    map_data = pd.DataFrame({
        "lat": [st.session_state.selected_lat],
        "lon": [st.session_state.selected_lon]
    })
    st.map(map_data, zoom=11)

with info_col:
    st.markdown("##### 📡 Data Source & Model Verification")
    st.write(f"**Primary Model:** Google DeepMind WeatherNext 3")
    st.write(f"**Active Source:** `{source_name}`")
    st.write(f"**Spatial Resolution:** 5x5 kilometer grid")
    st.write(f"**Temporal Frequency:** Hourly initialization from live satellite feeds")
    
    if not weather_info["is_google_api"]:
        st.info(
            "👉 To switch from the simulation feed to direct Google WeatherNext 3 API queries, "
            "add your Google Maps / Weather API key to your `.env` file (`GOOGLE_WEATHER_API_KEY=...`)."
        )

# Raw API Response Inspection
with st.expander("🛠️ Developer Tool: Inspect Raw WeatherNext 3 Payload"):
    st.json(weather_info.get("raw_response", {}))
