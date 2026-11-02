import os
from datetime import datetime, date, time, timedelta, timezone
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

from weathernext_service import WeatherNextService

try:
    from streamlit_js_eval import get_geolocation
    HAS_JS_EVAL = True
except ImportError:
    HAS_JS_EVAL = False


def get_thailand_now() -> datetime:
    """Returns the current datetime in Thailand timezone (ICT, UTC+7) regardless of cloud server location."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Bangkok")).replace(tzinfo=None)
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(hours=7)).replace(tzinfo=None)


def classify_precip_intensity(rate: float, units: str = "METRIC") -> str:
    """Classifies precipitation rate into standard intensity scales."""
    try:
        r = float(rate or 0.0)
    except Exception:
        r = 0.0

    if str(units).upper() == "IMPERIAL":
        if r < 0.002:
            return "Dry"
        elif r < 0.10:
            return "Light Rain"
        elif r < 0.30:
            return "Moderate Rain"
        elif r < 2.00:
            return "Heavy Rain"
        else:
            return "Torrential Rain"
    else:
        if r < 0.05:
            return "Dry"
        elif r < 2.5:
            return "Light Rain"
        elif r < 7.6:
            return "Moderate Rain"
        elif r < 50.0:
            return "Heavy Rain"
        else:
            return "Torrential Rain"


# Page Configuration
st.set_page_config(
    page_title="RainCheck — Google WeatherNext 3",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state=st.session_state.get("sidebar_state", "expanded")
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
.daily-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 12px 6px;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    margin-bottom: 10px;
}
.daily-card-rain {
    background: linear-gradient(180deg, #EFF6FF 0%, #FFFFFF 100%);
    border: 1.5px solid #93C5FD;
    border-radius: 12px;
    padding: 12px 6px;
    text-align: center;
    box-shadow: 0 4px 8px rgba(59, 130, 246, 0.15);
    margin-bottom: 10px;
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
    if st.session_state.get("device_gps_coords"):
        plat, plon = st.session_state.device_gps_coords
        paddr = WeatherNextService.reverse_geocode(plat, plon, st.session_state.get("google_api_key"))
        set_location(plat, plon, paddr)
    else:
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


# Auto-detect real device/phone GPS from the client's browser
if HAS_JS_EVAL:
    device_loc = get_geolocation(component_key="phone_browser_gps")
    if device_loc and isinstance(device_loc, dict) and "coords" in device_loc:
        coords = device_loc["coords"]
        dlat = round(float(coords["latitude"]), 4)
        dlon = round(float(coords["longitude"]), 4)
        if st.session_state.get("device_gps_coords") != (dlat, dlon):
            st.session_state["device_gps_coords"] = (dlat, dlon)
            st.session_state["is_device_gps"] = True
            dev_addr = WeatherNextService.reverse_geocode(dlat, dlon, st.session_state.get("google_api_key"))
            set_location(dlat, dlon, dev_addr)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ WeatherNext 3 Settings")
    env_google_key = os.getenv("GOOGLE_WEATHER_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not env_google_key:
        try:
            env_google_key = st.secrets.get("GOOGLE_WEATHER_API_KEY") or st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        except Exception:
            pass

    st.session_state.google_api_key = (env
