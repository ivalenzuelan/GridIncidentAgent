from __future__ import annotations
"""Lightweight wrapper around **AEMET OpenData** two‑step API.

Usage example:
    >>> client = AEMETClient()
    >>> data = client.get_municipal_forecast("Madrid")   # 7‑day forecast
    >>> obs  = client.get_station_observations("3195X")  # real‑time obs

The helper transparently performs the *wrapper ➜ datos* handshake.
Full Swagger: https://opendata.aemet.es/dist/index.html
"""

import os, json, zipfile, io, requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

_API = "https://opendata.aemet.es/opendata/api"
_KEY = os.getenv("AEMET_API_KEY")

if not _KEY:
    raise RuntimeError("AEMET_API_KEY missing in environment")

_TIMEOUT = int(os.getenv("AEMET_API_TIMEOUT", "30"))
_MAX_RETRIES = int(os.getenv("AEMET_API_RETRIES", "3"))

_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    max_retries=requests.adapters.Retry(
        total=_MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
)
_session.mount("https://", _adapter)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_json(url: str) -> Any:
    r = _session.get(url, timeout=_TIMEOUT)
    r.raise_for_status()
    if "application/zip" in r.headers.get("content-type", ""):
        z = zipfile.ZipFile(io.BytesIO(r.content))
        return json.loads(z.read(z.namelist()[0]).decode())
    return r.json()


def _aemet_call(endpoint: str) -> Any:
    """Perform the wrapper -> datos handshake for any endpoint."""
    wrapper = _get_json(f"{_API}{endpoint}?api_key={_KEY}")
    if wrapper.get("estado") != 200:
        raise RuntimeError(f"AEMET error {wrapper.get('estado')}: {wrapper.get('descripcion')}")
    return _get_json(wrapper["datos"])


# ---------------------------------------------------------------------------
# Client functions
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _municipality_code(name: str) -> str:
    """Return INE `idz_muni` for a municipality name (simple cache)."""
    name = name.lower()
    inv = _aemet_call("/valores/climatologicos/inventarioestaciones/todasestaciones")
    for row in inv:
        if row["nombre"].lower() == name and row["operativa"] == "SI":
            return row["indicativo"][:5]  # first 5 chars is INE code
    raise ValueError(f"Municipality '{name}' not found in AEMET inventory")


def get_municipal_forecast(city: str) -> List[Dict[str, Any]]:
    """7‑day municipal forecast for a Spanish city (INE code lookup)."""
    code = _municipality_code(city)
    return _aemet_call(f"/prediccion/especifica/municipio/diaria/{code}")


def get_station_observations(idema: str) -> List[Dict[str, Any]]:
    """Latest hourly observations for a station (e.g. '3195X')."""
    return _aemet_call(f"/observacion/convencional/datos/estacion/{idema}")


def get_lightning_last_hour() -> Dict[str, Any]:
    """GeoJSON with lightning strikes in the last hour across Spain."""
    return _aemet_call("/rayos/1h")


def get_climatology_series(idema: str, year: int) -> List[Dict[str, Any]]:
    """Daily climatology for a station & year (returns list of dicts)."""
    return _aemet_call(
        f"/valores/climatologicos/diarios/datos/anio/{year}/estacion/{idema}"
    )


# ---------------------------------------------------------------------------
# Minimal CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Fetching 7‑day forecast for Madrid…")
    fc = get_municipal_forecast("Madrid")
    print(json.dumps(fc[0]["prediccion"]["dia"][0], indent=2, ensure_ascii=False))

    print("\nLast‑hour lightning strikes:")
    strikes = get_lightning_last_hour()
    print(strikes.keys(), len(strikes.get("features", [])), "strikes")

class AEMETClient:
    """Mock AEMET API client for testing purposes."""
    
    def __init__(self):
        """Initialize the mock AEMET client."""
        load_dotenv()
        self.api_key = os.getenv("AEMET_API_KEY", "dummy_key")
        self.base_url = "https://opendata.aemet.es/opendata/api"
        self.timeout = 30
        self.retries = 3

    def get_observations(self, location: str) -> dict:
        """Get mock weather observations for a location."""
        # Return mock data for testing
        return {
            "temperature": 22.5,
            "humidity": 65.0,
            "wind_speed": 15.0,
            "precipitation": 0.0,
            "conditions": "Clear"
        }

    def get_forecast(self, location: str) -> dict:
        """Get mock weather forecast for a location."""
        return {
            "forecast": [
                {
                    "date": datetime.now().isoformat(),
                    "temperature": {"max": 25.0, "min": 18.0},
                    "precipitation": 0.0,
                    "conditions": "Clear"
                }
            ]
        }

    def get_historical_data(self, location: str, start_date: datetime, end_date: datetime) -> dict:
        """Get mock historical weather data."""
        return {
            "historical": [
                {
                    "date": start_date.isoformat(),
                    "temperature": 22.0,
                    "humidity": 70.0,
                    "wind_speed": 12.0,
                    "precipitation": 0.0,
                    "conditions": "Partly Cloudy"
                }
            ]
        }
