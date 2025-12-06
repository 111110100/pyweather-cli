import sys
import geopy
import requests
from geopy.geocoders import Nominatim


# Helper to get current location based on IP
def get_current_location():
    try:
        resp = requests.get("https://ipinfo.io/json")
        resp.raise_for_status()
        data = resp.json()
        city = data.get("city")
        region = data.get("region")
        country = data.get("country")
        if city and region and country:
            return f"{city}, {region}, {country}"
        elif city and country:
            return f"{city}, {country}"
        else:
            return "San Francisco, CA"
    except Exception:
        return "San Francisco, CA"


# Helper for wind direction
def deg_to_compass(num):
    val = int((num / 22.5) + 0.5)
    arr = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    return arr[(val % 16)]


# Map Open-Meteo weathercode to description
def weather_description(code):
    """Return human readable weather condition for Open-Meteo weathercode."""
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, "Unknown")


if __name__ == "__main__":
    # First command line argument is location in string, if empty use "San Francisco, CA"
    if len(sys.argv) > 1:
        location = sys.argv[1]
    else:
        location = get_current_location()

    try:
        geolocator = Nominatim(user_agent="Mozilla/5.0")
        location = geolocator.geocode(location)
        if location is None:
            print("Error: Could not find location.")
            exit(1)
    except geopy.exc.GeocoderQueryError as err:
        print("Could not get location: ", err)
        exit(1)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "current_weather": "true",
        "hourly": "precipitation_probability",
        "temperature_unit": "fahrenheit",
        "windspeed_unit": "mph",
    }

    try:
        result = requests.get(url, params=params)
        result.raise_for_status()
    except requests.RequestException as err:
        print("Could not get weather: ", err)
        exit(1)

    data = result.json()

    if "current_weather" not in data:
        print("Could not get weather data from response")
        exit(1)

    current = data["current_weather"]
    # Get precipitation for the current hour
    # Open-Meteo returns ISO8601 time strings. We can just take the first element of hourly data
    # assuming the API returns data starting from now or close to it, but to be precise we should match time.
    # However, for simplicity in this CLI, taking the current index based on local time vs server time can be tricky.
    # A simple approximation is taking the first element if we assume the query is for "now".
    # Actually, Open-Meteo 'current_weather' doesn't have precipitation.
    # We requested 'hourly=precipitation_probability'.
    # Let's find the index in 'hourly.time' that matches 'current_weather.time'
    try:
        current_time = current["time"]
        time_index = data["hourly"]["time"].index(current_time)
        precip_prob = data["hourly"]["precipitation_probability"][time_index]
    except (KeyError, ValueError):
        precip_prob = 0  # Fallback

    # Display
    print(f"Current weather for {location.address}:")
    print(f"Tempreture: {current['temperature']} F ({(current['temperature'] - 32) * 5 / 9:.1f} C)")
    print(f"Wind speed: {current['windspeed']} mph")
    print(f"Wind direction: {deg_to_compass(current['winddirection'])}")
    print(f"Condition: {weather_description(current['weathercode'])}")
    print(f"Chance of precipitation: {precip_prob}% ")
