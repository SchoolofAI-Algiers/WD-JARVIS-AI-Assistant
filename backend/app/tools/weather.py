import requests


class WeatherError(Exception):
    pass


class WeatherTool:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def get_weather(self, city: str) -> dict:
        location = self._find_city(city)

        if not location:
            raise WeatherError(
                f"Could not find the location '{city}'."
            )

        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "weather_code,"
                "wind_speed_10m"
            ),
            "timezone": "auto",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise WeatherError(
                "Weather service is currently unavailable."
            ) from error

        data = response.json()

        current = data.get("current")

        if not current:
            raise WeatherError(
                "Weather data was not available."
            )

        return {
            "city": location["name"],
            "country": location.get("country"),
            "temperature": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "weather_code": current["weather_code"],
            "wind_speed": current["wind_speed_10m"],
            "timezone": data.get("timezone"),
        }

    def _find_city(self, city: str) -> dict | None:
        params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        }

        try:
            response = requests.get(
                self.GEOCODING_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise WeatherError(
                "Location service is currently unavailable."
            ) from error

        results = response.json().get("results", [])

        if not results:
            return None

        return results[0]

    def describe_weather_code(self, code: int) -> str:
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }

        return descriptions.get(
            code,
            "Unknown conditions",
        )


weather_tool = WeatherTool()