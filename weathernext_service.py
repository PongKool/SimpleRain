import os
import requests
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

def safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """
    Safely retrieve nested dictionary keys without raising AttributeError or TypeError
    if intermediate keys are missing or set to None (JSON null).
    """
    curr = obj
    for k in keys:
        if not isinstance(curr, dict):
            return default
        curr = curr.get(k)
        if curr is None:
            return default
    return curr if curr is not None else default

class WeatherNextService:
    """
    Service for checking weather and rain conditions using Google's WeatherNext 3
    via the Google Maps Platform Weather API (weather.googleapis.com).
    Provides seamless fallback to Open-Meteo when no Google API key is supplied.
    """
    GOOGLE_WEATHER_BASE_URL = "https://weather.googleapis.com/v1"
    NOMINATIM_GEOCODE_URL = "https://nominatim.openstreetmap.org/search"

    @staticmethod
    def get_location_now(tz_name: str = "Asia/Bangkok") -> datetime:
        """
        Returns the current local datetime in Thailand (or specified timezone)
        regardless of whether the code runs on a local machine or a UTC cloud server.
        """
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None)
        except Exception:
            return (datetime.now(timezone.utc) + timedelta(hours=7)).replace(tzinfo=None)

    @staticmethod
    def detect_current_location() -> Dict[str, Any]:
        """
        Auto-detect current location via IP geolocation.
        Defaults to Bangkok, Thailand if detection fails.
        """
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    city = data.get("city", "")
                    country = data.get("country", "")
                    region = data.get("regionName", "")
                    display_name = f"{city}, {country}" if city else country or "Current Location"
                    return {
                        "name": display_name,
                        "city": city,
                        "region": region,
                        "country": country,
                        "latitude": float(data.get("lat", 13.7563)),
                        "longitude": float(data.get("lon", 100.5018)),
                        "timezone": data.get("timezone", "UTC"),
                        "detected": True
                    }
        except Exception:
            pass

        # Fallback default
        return {
            "name": "Bangkok, Thailand",
            "city": "Bangkok",
            "region": "Bangkok",
            "country": "Thailand",
            "latitude": 13.7563,
            "longitude": 100.5018,
            "timezone": "Asia/Bangkok",
            "detected": False
        }

    @staticmethod
    def geocode_location(query: str, google_key: Optional[str] = None) -> Optional[Tuple[float, float, str]]:
        """
        Geocode a location query string (city, address, landmark) into (latitude, longitude, display_name).
        """
        query = query.strip()
        if not query:
            return None

        # Check if input is already "lat, lon"
        if "," in query:
            parts = query.split(",")
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return lat, lon, f"Coordinates ({lat:.4f}, {lon:.4f})"
                except ValueError:
                    pass

        # If Google key is provided, try Google Maps Geocoding API
        if google_key:
            try:
                g_url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {"address": query, "key": google_key}
                resp = requests.get(g_url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "OK" and data.get("results"):
                        res0 = data["results"][0]
                        lat = res0["geometry"]["location"]["lat"]
                        lon = res0["geometry"]["location"]["lng"]
                        name = res0.get("formatted_address", query)
                        return float(lat), float(lon), name
            except Exception:
                pass

        # Fallback to OpenStreetMap Nominatim
        try:
            headers = {"User-Agent": "SimpleRainWeatherNextApp/1.0"}
            params = {"q": query, "format": "json", "limit": 1}
            resp = requests.get(WeatherNextService.NOMINATIM_GEOCODE_URL, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                results = resp.json()
                if results and len(results) > 0:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    name = results[0].get("display_name", query)
                    return lat, lon, name
        except Exception:
            pass

        return None

    @classmethod
    def reverse_geocode(cls, lat: float, lon: float, google_key: Optional[str] = None) -> str:
        """
        Reverse geocodes latitude, longitude into a human-readable city/address.
        """
        if google_key:
            try:
                g_url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {"latlng": f"{lat},{lon}", "key": google_key}
                resp = requests.get(g_url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "OK" and data.get("results"):
                        return data["results"][0].get("formatted_address", f"GPS ({lat:.4f}, {lon:.4f})")
            except Exception:
                pass

        try:
            headers = {"User-Agent": "SimpleRainWeatherNextApp/1.0"}
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {"lat": lat, "lon": lon, "format": "json"}
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                addr = data.get("address", {})
                city = addr.get("city") or addr.get("town") or addr.get("suburb") or addr.get("state") or ""
                country = addr.get("country", "")
                if city and country:
                    return f"{city}, {country}"
                elif data.get("display_name"):
                    parts = data["display_name"].split(",")
                    return ", ".join(parts[:2]).strip()
        except Exception:
            pass

        return f"Device GPS ({lat:.4f}, {lon:.4f})"

    @classmethod
    def get_weather_data(
        cls,
        lat: float,
        lon: float,
        target_time: Optional[datetime] = None,
        google_api_key: Optional[str] = None,
        units: str = "METRIC"
    ) -> Dict[str, Any]:
        """
        Query weather conditions using Google Maps Weather API (WeatherNext 3)
        or fallback to Open-Meteo if no key is provided.
        """
        if google_api_key:
            try:
                return cls._query_google_weathernext(lat, lon, target_time, google_api_key, units)
            except Exception as e:
                # If Google API call fails, fall back and note the error
                fallback_data = cls._query_open_meteo(lat, lon, target_time, units)
                fallback_data["api_warning"] = f"Google WeatherNext 3 API query returned: {str(e)}. Using fallback forecast data."
                return fallback_data
        else:
            return cls._query_open_meteo(lat, lon, target_time, units)

    @classmethod
    def get_7day_forecast(
        cls,
        lat: float,
        lon: float,
        google_api_key: Optional[str] = None,
        units: str = "METRIC"
    ) -> Dict[str, Any]:
        """
        Query 7-day daily weather forecast using Google Maps Weather API (WeatherNext 3)
        or fallback to Open-Meteo if no key is provided.
        """
        if google_api_key:
            try:
                return cls._query_google_7day_forecast(lat, lon, google_api_key, units)
            except Exception as e:
                fallback_data = cls._query_open_meteo_7day_forecast(lat, lon, units)
                fallback_data["api_warning"] = f"Google WeatherNext 3 API query returned: {str(e)}. Using fallback 7-day forecast."
                return fallback_data
        else:
            return cls._query_open_meteo_7day_forecast(lat, lon, units)

    @classmethod
    def _query_google_7day_forecast(
        cls,
        lat: float,
        lon: float,
        api_key: str,
        units: str = "METRIC"
    ) -> Dict[str, Any]:
        url = f"{cls.GOOGLE_WEATHER_BASE_URL}/forecast/days:lookup"
        params = {
            "key": api_key,
            "location.latitude": lat,
            "location.longitude": lon,
            "days": 7,
            "unitsSystem": units
        }
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            raise RuntimeError(f"Google Weather API daily forecast HTTP {resp.status_code}")

        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("Invalid JSON response from Google Weather API")

        forecast_days = data.get("forecastDays") or []
        if not forecast_days or not isinstance(forecast_days, list):
            raise RuntimeError("No daily forecast data returned from Google Weather API")

        daily_list = []
        rain_keywords = ["RAIN", "DRIZZLE", "SHOWER", "THUNDERSTORM", "DOWNPOUR", "STORM", "PRECIPITATION"]
        today_date = cls.get_location_now().date()

        for idx, fd in enumerate(forecast_days[:7]):
            if not isinstance(fd, dict):
                continue

            dt = None
            for date_key in ["displayDateTime", "forecastDate", "date"]:
                date_obj = fd.get(date_key)
                if isinstance(date_obj, dict):
                    y = safe_get(date_obj, "year")
                    m = safe_get(date_obj, "month")
                    d = safe_get(date_obj, "day")
                    if y and m and d:
                        try:
                            dt = date(int(y), int(m), int(d))
                            break
                        except Exception:
                            pass
                elif isinstance(date_obj, str) and date_obj:
                    try:
                        clean_str = date_obj.split("T")[0]
                        dt = datetime.strptime(clean_str, "%Y-%m-%d").date()
                        break
                    except Exception:
                        pass

            if dt is None:
                dt = today_date + timedelta(days=idx)

            date_str = dt.strftime("%Y-%m-%d")
            day_name = dt.strftime("%a")
            date_display = dt.strftime("%a, %b %d")

            cond_text = str(safe_get(fd, "weatherCondition", "description", "text", default="Clear") or "Clear")
            cond_type = str(safe_get(fd, "weatherCondition", "type", default="") or "").upper()
            icon_uri = str(safe_get(fd, "weatherCondition", "iconBaseUri", default="") or "")
            if icon_uri and not icon_uri.endswith(".png") and not icon_uri.endswith(".svg"):
                icon_uri = f"{icon_uri}.png"

            t_max = float(safe_get(fd, "maxTemperature", "degrees", default=0.0) or 0.0)
            t_min = float(safe_get(fd, "minTemperature", "degrees", default=0.0) or 0.0)

            daytime = fd.get("daytimeForecast")

            prob = safe_get(fd, "precipitation", "probability", "percent")
            if prob is None:
                prob = safe_get(daytime, "precipitation", "probability", "percent")
            if prob is None:
                prob = safe_get(fd, "precipitationProbability")
            if prob is None:
                prob = safe_get(daytime, "precipitationProbability", default=0)
            prob = int(prob or 0)

            qpf = safe_get(fd, "precipitation", "qpf", "quantity")
            if qpf is None:
                qpf = safe_get(daytime, "precipitation", "qpf", "quantity")
            if qpf is None:
                qpf = safe_get(fd, "precipitation", "rain", "quantity", default=0.0)
            qpf = float(qpf or 0.0)

            is_rain_day = (
                any(k in cond_type or k in cond_text.upper() for k in rain_keywords)
                or qpf > 0.5
                or prob >= 50
            )

            daily_list.append({
                "date": date_str,
                "day_name": day_name,
                "date_display": date_display,
                "condition_text": cond_text,
                "icon_url": icon_uri,
                "temp_max": t_max,
                "temp_min": t_min,
                "temp_unit": "°C" if units == "METRIC" else "°F",
                "precipitation_sum": round(qpf, 1),
                "precipitation_unit": "mm" if units == "METRIC" else "in",
                "rain_prob": prob,
                "is_raining": is_rain_day
            })

        tz_name = str(safe_get(data, "timeZone", "id", default="Asia/Bangkok") or "Asia/Bangkok")

        return {
            "source": "Google WeatherNext 3 (Google Maps Platform Weather API)",
            "is_google_api": True,
            "timezone": tz_name,
            "utc_offset": "UTC+7" if "Bangkok" in tz_name else "",
            "daily_forecast": daily_list
        }

    @classmethod
    def _query_open_meteo_7day_forecast(
        cls,
        lat: float,
        lon: float,
        units: str = "METRIC"
    ) -> Dict[str, Any]:
        temp_unit = "celsius" if units == "METRIC" else "fahrenheit"
        precip_unit = "mm" if units == "METRIC" else "inch"

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
            "temperature_unit": temp_unit,
            "precipitation_unit": precip_unit,
            "timezone": "auto",
            "forecast_days": 7
        }

        resp = requests.get(url, params=params, timeout=6)
        if resp.status_code != 200:
            raise RuntimeError(f"Open-Meteo API query error: HTTP {resp.status_code}")

        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("Invalid JSON response from Open-Meteo API")

        daily = data.get("daily") or {}

        times = daily.get("time") or []
        codes = daily.get("weather_code") or []
        t_maxs = daily.get("temperature_2m_max") or []
        t_mins = daily.get("temperature_2m_min") or []
        precips = daily.get("precipitation_sum") or []
        probs = daily.get("precipitation_probability_max") or []

        today_date = cls.get_location_now().date()
        daily_list = []
        for i in range(len(times)):
            t_str = str(times[i])
            try:
                dt = datetime.strptime(t_str, "%Y-%m-%d").date()
            except Exception:
                dt = today_date + timedelta(days=i)

            w_code = codes[i] if i < len(codes) and codes[i] is not None else 0
            cond_text, is_rain_wmo, icon_url = cls._map_wmo_code(w_code)

            p_sum = float(precips[i]) if i < len(precips) and precips[i] is not None else 0.0
            p_prob = int(probs[i]) if i < len(probs) and probs[i] is not None else 0

            is_rain_day = is_rain_wmo or p_sum > 0.5 or p_prob >= 50

            daily_list.append({
                "date": dt.strftime("%Y-%m-%d"),
                "day_name": dt.strftime("%a"),
                "date_display": dt.strftime("%a, %b %d"),
                "condition_text": cond_text,
                "icon_url": icon_url,
                "temp_max": float(t_maxs[i]) if i < len(t_maxs) and t_maxs[i] is not None else 0.0,
                "temp_min": float(t_mins[i]) if i < len(t_mins) and t_mins[i] is not None else 0.0,
                "temp_unit": "°C" if units == "METRIC" else "°F",
                "precipitation_sum": round(p_sum, 1),
                "precipitation_unit": "mm" if units == "METRIC" else "in",
                "rain_prob": p_prob,
                "is_raining": is_rain_day
            })

        tz_name = str(data.get("timezone") or "Asia/Bangkok")
        utc_sec = int(data.get("utc_offset_seconds") or 25200)
        offset_h = int(utc_sec / 3600)
        offset_str = f"UTC{'+' if offset_h >= 0 else ''}{offset_h}"

        return {
            "source": "Open-Meteo Realtime Engine (Google WeatherNext 3 Compatible Simulation)",
            "is_google_api": False,
            "timezone": tz_name,
            "utc_offset": offset_str,
            "daily_forecast": daily_list
        }

    @staticmethod
    def _extract_google_local_time(fh: Dict[str, Any]) -> Tuple[datetime, str]:
        """
        Extract local datetime and formatted label from Google Weather API forecastHour.
        Uses displayDateTime (local time at coordinates) rather than UTC interval.startTime.
        """
        disp = fh.get("displayDateTime")
        if isinstance(disp, dict) and "year" in disp and "hours" in disp:
            try:
                y = int(disp.get("year", 2026))
                m = int(disp.get("month", 1))
                d = int(disp.get("day", 1))
                h = int(disp.get("hours", 0))
                minute = int(disp.get("minutes", 0))
                dt = datetime(y, m, d, h, minute)
                return dt, dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        # Fallback to interval.startTime (+7 hours for Thailand if ends with Z)
        iso = fh.get("interval", {}).get("startTime", "")
        if iso:
            try:
                clean_iso = iso.replace("Z", "+00:00")
                dt_utc = datetime.fromisoformat(clean_iso)
                dt_local = dt_utc + timedelta(hours=7)
                return dt_local.replace(tzinfo=None), dt_local.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return cls.get_location_now(), cls.get_location_now().strftime("%Y-%m-%d %H:%M")

    @classmethod
    def _query_google_weathernext(
        cls,
        lat: float,
        lon: float,
        target_time: Optional[datetime],
        api_key: str,
        units: str = "METRIC"
    ) -> Dict[str, Any]:
        """
        Calls Google Maps Platform Weather API endpoints powered by WeatherNext 3.
        Supports both real-time ('now') and target datetime forecast/history in local Thailand time.
        """
        is_now = target_time is None
        now_dt = cls.get_location_now()

        # 1. Fetch Current Conditions
        current_url = f"{cls.GOOGLE_WEATHER_BASE_URL}/currentConditions:lookup"
        current_params = {
            "key": api_key,
            "location.latitude": lat,
            "location.longitude": lon,
            "unitsSystem": units
        }
        resp_curr = requests.get(current_url, params=current_params, timeout=8)
        curr_data = resp_curr.json() if resp_curr.status_code == 200 else {}

        # 2. Fetch Hourly Forecast
        hours_needed = 24
        if not is_now and target_time:
            delta_h = int((target_time - now_dt).total_seconds() / 3600.0)
            if delta_h > 0:
                hours_needed = min(240, max(24, delta_h + 12))

        forecast_url = f"{cls.GOOGLE_WEATHER_BASE_URL}/forecast/hours:lookup"
        forecast_params = {
            "key": api_key,
            "location.latitude": lat,
            "location.longitude": lon,
            "hours": hours_needed,
            "unitsSystem": units
        }
        resp_forecast = requests.get(forecast_url, params=forecast_params, timeout=8)
        forecast_hours = []
        if resp_forecast.status_code == 200:
            forecast_hours = resp_forecast.json().get("forecastHours", [])

        # Parse timeline using exact local time
        timeline = []
        for fh in forecast_hours:
            if not isinstance(fh, dict):
                continue
            dt_local, t_str = cls._extract_google_local_time(fh)
            fh_type = str(safe_get(fh, "weatherCondition", "type", default="") or "")
            fh_desc = str(safe_get(fh, "weatherCondition", "description", "text", default="") or "")
            fh_prob = safe_get(fh, "precipitation", "probability", "percent")
            if fh_prob is None:
                fh_prob = safe_get(fh, "precipitationProbability", default=0)
            fh_qpf = safe_get(fh, "precipitation", "qpf", "quantity", default=0.0)
            timeline.append({
                "time": t_str,
                "dt": dt_local,
                "temp": safe_get(fh, "temperature", "degrees", default=0),
                "condition": fh_desc or fh_type,
                "rain_prob": int(fh_prob or 0),
                "precipitation": float(fh_qpf or 0.0)
            })

        rain_keywords = ["RAIN", "DRIZZLE", "SHOWER", "THUNDERSTORM", "DOWNPOUR", "STORM", "PRECIPITATION"]

        if is_now or not forecast_hours:
            # Use current conditions
            cond_text = str(safe_get(curr_data, "weatherCondition", "description", "text", default="Unknown") or "Unknown")
            cond_type = str(safe_get(curr_data, "weatherCondition", "type", default="") or "").upper()
            icon_uri = str(safe_get(curr_data, "weatherCondition", "iconBaseUri", default="") or "")
            if icon_uri and not icon_uri.endswith(".png") and not icon_uri.endswith(".svg"):
                icon_uri = f"{icon_uri}.png"

            temp_deg = float(safe_get(curr_data, "temperature", "degrees", default=0.0) or 0.0)
            humidity = int(safe_get(curr_data, "relativeHumidity", default=0) or 0)
            precip_val = float(safe_get(curr_data, "precipitation", "value", default=0.0) or 0.0)
            precip_prob = int(safe_get(curr_data, "precipitationProbability", default=0) or 0)

            is_raining = any(k in cond_type or k in cond_text.upper() for k in rain_keywords) or (precip_val > 0.05)
            matched_time_str = cls.get_location_now().strftime("%Y-%m-%d %H:%M")
        else:
            # Match target hour in forecastHours using exact local time
            best_fh = forecast_hours[0] if isinstance(forecast_hours[0], dict) else {}
            best_time_str = target_time.strftime("%Y-%m-%d %H:%M")
            min_diff = float("inf")
            for fh in forecast_hours:
                if not isinstance(fh, dict):
                    continue
                dt_local, t_str = cls._extract_google_local_time(fh)
                diff = abs((dt_local - target_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    best_fh = fh
                    best_time_str = t_str

            cond_text = str(safe_get(best_fh, "weatherCondition", "description", "text", default="Unknown") or "Unknown")
            cond_type = str(safe_get(best_fh, "weatherCondition", "type", default="") or "").upper()
            icon_uri = str(safe_get(best_fh, "weatherCondition", "iconBaseUri", default="") or "")
            if icon_uri and not icon_uri.endswith(".png") and not icon_uri.endswith(".svg"):
                icon_uri = f"{icon_uri}.png"

            temp_deg = float(safe_get(best_fh, "temperature", "degrees", default=0.0) or 0.0)
            humidity = int(safe_get(best_fh, "relativeHumidity", default=0) or 0)
            precip_prob = safe_get(best_fh, "precipitation", "probability", "percent")
            if precip_prob is None:
                precip_prob = safe_get(best_fh, "precipitationProbability", default=0)
            precip_prob = int(precip_prob or 0)

            precip_val = float(safe_get(best_fh, "precipitation", "qpf", "quantity", default=0.0) or 0.0)

            is_raining = any(k in cond_type or k in cond_text.upper() for k in rain_keywords) or (precip_val > 0.05) or (precip_prob >= 60 and "RAIN" in cond_text.upper())
            matched_time_str = best_time_str

        tz_name = str(safe_get(curr_data, "timeZone", "id", default="Asia/Bangkok") or "Asia/Bangkok")

        return {
            "source": "Google WeatherNext 3 (Google Maps Platform Weather API)",
            "is_google_api": True,
            "timezone": tz_name,
            "utc_offset": "UTC+7" if "Bangkok" in tz_name else "",
            "target_time_label": matched_time_str,
            "is_raining": is_raining,
            "condition_text": cond_text,
            "condition_type": cond_type,
            "icon_url": icon_uri,
            "temperature": temp_deg,
            "temperature_unit": "°C" if units == "METRIC" else "°F",
            "humidity": humidity,
            "precipitation_rate": precip_val,
            "precipitation_unit": "mm" if units == "METRIC" else "in",
            "precipitation_prob": int(precip_prob),
            "timeline": timeline[:24],
            "raw_response": {
                "current": curr_data,
                "forecast_sample": forecast_hours[:2] if forecast_hours else []
            }
        }

    @classmethod
    def _query_open_meteo(
        cls,
        lat: float,
        lon: float,
        target_time: Optional[datetime],
        units: str = "METRIC"
    ) -> Dict[str, Any]:
        """
        Fallback weather source when Google API Key is not configured.
        Accurately evaluates whether it is raining at the specified target_time.
        """
        temp_unit = "celsius" if units == "METRIC" else "fahrenheit"
        precip_unit = "mm" if units == "METRIC" else "inch"

        now_dt = cls.get_location_now()
        is_now = target_time is None

        forecast_days = 3
        past_days = 0

        if not is_now and target_time:
            delta_days = (target_time.date() - now_dt.date()).days
            if delta_days >= 0:
                forecast_days = max(3, min(14, delta_days + 3))
            else:
                past_days = max(1, min(7, abs(delta_days) + 1))

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,showers,weather_code",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,rain,weather_code",
            "temperature_unit": temp_unit,
            "precipitation_unit": precip_unit,
            "timezone": "auto",
            "forecast_days": forecast_days,
            "past_days": past_days
        }

        resp = requests.get(url, params=params, timeout=6)
        if resp.status_code != 200:
            raise RuntimeError(f"Open-Meteo API query error: HTTP {resp.status_code}")

        data = resp.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})

        times = hourly.get("time", [])
        probs = hourly.get("precipitation_probability", [])
        precips = hourly.get("precipitation", [])
        temps = hourly.get("temperature_2m", [])
        humids = hourly.get("relative_humidity_2m", [])
        codes = hourly.get("weather_code", [])

        # If checking right now
        if is_now or not times:
            weather_code = current.get("weather_code", 0)
            cond_text, is_raining, icon_url = cls._map_wmo_code(weather_code)
            current_rain = float(current.get("rain", 0.0) or current.get("precipitation", 0.0) or current.get("showers", 0.0))
            if current_rain > 0.05:
                is_raining = True
            temp_val = current.get("temperature_2m", 0.0)
            humidity_val = current.get("relative_humidity_2m", 0)
            prob_val = probs[0] if probs else (80 if is_raining else 10)
            target_idx = 0
            matched_time_str = "Now (Real-time)"
        else:
            # Find the hourly entry closest to target_time
            target_str = target_time.strftime("%Y-%m-%dT%H:00")
            best_idx = 0
            min_diff = float("inf")

            for idx, t in enumerate(times):
                try:
                    entry_dt = datetime.fromisoformat(t)
                    diff = abs((entry_dt - target_time).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        best_idx = idx
                except Exception:
                    continue

            target_idx = best_idx
            weather_code = codes[target_idx] if target_idx < len(codes) else 0
            cond_text, is_raining, icon_url = cls._map_wmo_code(weather_code)

            current_rain = float(precips[target_idx]) if target_idx < len(precips) else 0.0
            if current_rain > 0.05:
                is_raining = True

            prob_val = probs[target_idx] if target_idx < len(probs) else 0
            if prob_val >= 60 and not is_raining and "Rain" in cond_text:
                is_raining = True

            temp_val = temps[target_idx] if target_idx < len(temps) else 0.0
            humidity_val = humids[target_idx] if target_idx < len(humids) else 0
            matched_time_str = times[target_idx].replace("T", " ")

        # Build timeline around the target index (show 24 hours starting from max(0, target_idx - 2))
        start_slice = max(0, target_idx - 2)
        end_slice = min(len(times), start_slice + 24)
        timeline = []
        for i in range(start_slice, end_slice):
            h_code = codes[i] if i < len(codes) else 0
            h_desc, _, _ = cls._map_wmo_code(h_code)
            timeline.append({
                "time": times[i],
                "temp": temps[i] if i < len(temps) else 0,
                "condition": h_desc,
                "rain_prob": probs[i] if i < len(probs) else 0,
                "precipitation": precips[i] if i < len(precips) else 0.0
            })

        tz_name = data.get("timezone", "Asia/Bangkok")
        utc_sec = data.get("utc_offset_seconds", 25200)
        offset_h = int(utc_sec / 3600)
        offset_str = f"UTC{'+' if offset_h >= 0 else ''}{offset_h}"

        return {
            "source": "Open-Meteo Realtime Engine (Google WeatherNext 3 Compatible Simulation)",
            "is_google_api": False,
            "timezone": tz_name,
            "utc_offset": offset_str,
            "target_time_label": matched_time_str,
            "is_raining": is_raining,
            "condition_text": cond_text,
            "condition_type": "RAIN" if is_raining else "NORMAL",
            "icon_url": icon_url,
            "temperature": temp_val,
            "temperature_unit": "°C" if units == "METRIC" else "°F",
            "humidity": humidity_val,
            "precipitation_rate": current_rain,
            "precipitation_unit": "mm" if units == "METRIC" else "in",
            "precipitation_prob": prob_val,
            "timeline": timeline,
            "raw_response": current if is_now else {
                "target_hour": times[target_idx] if target_idx < len(times) else "",
                "weather_code": weather_code,
                "precipitation": current_rain,
                "precipitation_probability": prob_val,
                "temperature": temp_val
            }
        }

    @staticmethod
    def _map_wmo_code(code: int) -> Tuple[str, bool, str]:
        """
        Map WMO weather code to condition description, is_raining flag, and icon.
        """
        wmo_map = {
            0: ("Clear sky", False, "https://maps.gstatic.com/weather/v1/sunny.png"),
            1: ("Mainly clear", False, "https://maps.gstatic.com/weather/v1/mostly_sunny.png"),
            2: ("Partly cloudy", False, "https://maps.gstatic.com/weather/v1/partly_cloudy.png"),
            3: ("Overcast", False, "https://maps.gstatic.com/weather/v1/cloudy.png"),
            45: ("Fog", False, "https://maps.gstatic.com/weather/v1/fog.png"),
            48: ("Depositing rime fog", False, "https://maps.gstatic.com/weather/v1/fog.png"),
            51: ("Light drizzle", True, "https://maps.gstatic.com/weather/v1/rain.png"),
            53: ("Moderate drizzle", True, "https://maps.gstatic.com/weather/v1/rain.png"),
            55: ("Dense drizzle", True, "https://maps.gstatic.com/weather/v1/heavy_rain.png"),
            61: ("Slight rain", True, "https://maps.gstatic.com/weather/v1/rain.png"),
            63: ("Moderate rain", True, "https://maps.gstatic.com/weather/v1/rain.png"),
            65: ("Heavy rain", True, "https://maps.gstatic.com/weather/v1/heavy_rain.png"),
            66: ("Freezing rain", True, "https://maps.gstatic.com/weather/v1/rain.png"),
            67: ("Heavy freezing rain", True, "https://maps.gstatic.com/weather/v1/heavy_rain.png"),
            71: ("Slight snow fall", False, "https://maps.gstatic.com/weather/v1/snow.png"),
            73: ("Moderate snow fall", False, "https://maps.gstatic.com/weather/v1/snow.png"),
            75: ("Heavy snow fall", False, "https://maps.gstatic.com/weather/v1/heavy_snow.png"),
            80: ("Slight rain showers", True, "https://maps.gstatic.com/weather/v1/scattered_showers.png"),
            81: ("Moderate rain showers", True, "https://maps.gstatic.com/weather/v1/scattered_showers.png"),
            82: ("Violent rain showers", True, "https://maps.gstatic.com/weather/v1/heavy_rain.png"),
            95: ("Thunderstorm", True, "https://maps.gstatic.com/weather/v1/thunderstorm.png"),
            96: ("Thunderstorm with slight hail", True, "https://maps.gstatic.com/weather/v1/thunderstorm.png"),
            99: ("Thunderstorm with heavy hail", True, "https://maps.gstatic.com/weather/v1/thunderstorm.png"),
        }
        return wmo_map.get(code, ("Cloudy", False, "https://maps.gstatic.com/weather/v1/cloudy.png"))
