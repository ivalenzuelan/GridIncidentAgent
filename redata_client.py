from datetime import datetime
from typing import Optional, Literal, List
import requests
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Type definitions for API parameters
Lang = Literal["es", "en"]
TimeTrunc = Literal["hour", "day", "month", "year"]
GeoLimit = Literal["peninsular", "canarias", "baleares", "ceuta", "melilla", "ccaa"]

class REDataClient:
    """Client for interacting with the REData API."""
    
    BASE_URL = os.getenv("REDATA_API_BASE_URL", "https://apidatos.ree.es")
    TIMEOUT = int(os.getenv("REDATA_API_TIMEOUT", "30"))
    MAX_RETRIES = int(os.getenv("REDATA_API_RETRIES", "3"))
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Configure retry strategy
        retry_strategy = requests.adapters.Retry(
            total=self.MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
    
    def get_widget_data(
        self,
        lang: Lang,
        category: str,
        widget: str,
        start_date: datetime,
        end_date: datetime,
        time_trunc: TimeTrunc,
        geo_trunc: Optional[Literal["electric_system"]] = None,
        geo_limit: Optional[GeoLimit] = None,
        geo_ids: Optional[str] = None
    ) -> dict:
        """
        Get widget data from the REData API.
        
        Args:
            lang: Language of the response ("es" or "en")
            category: General category of the widget
            widget: Specific widget to retrieve
            start_date: Start date in ISO 8601 format
            end_date: End date in ISO 8601 format
            time_trunc: Time aggregation ("hour", "day", "month", "year")
            geo_trunc: Optional geographical scope (currently only "electric_system")
            geo_limit: Optional electrical system or region
            geo_ids: Optional ID of the autonomous community/electrical system
            
        Returns:
            dict: JSON response from the API
        """
        # Build the URL
        url = f"{self.BASE_URL}/{lang}/datos/{category}/{widget}"
        
        # Build query parameters
        params = {
            "start_date": start_date.strftime("%Y-%m-%dT%H:%M"),
            "end_date": end_date.strftime("%Y-%m-%dT%H:%M"),
            "time_trunc": time_trunc
        }
        
        # Add optional parameters if provided
        if geo_trunc:
            params["geo_trunc"] = geo_trunc
        if geo_limit:
            params["geo_limit"] = geo_limit
        if geo_ids:
            params["geo_ids"] = geo_ids
            
        # Make the request with timeout
        response = self.session.get(url, params=params, timeout=self.TIMEOUT)
        response.raise_for_status()
        
        return response.json()

# Example usage:
if __name__ == "__main__":
    client = REDataClient()
    
    # Example: Get daily balance for January 2019
    start_date = datetime(2019, 1, 1)
    end_date = datetime(2019, 1, 31, 23, 59)
    
    try:
        data = client.get_widget_data(
            lang="es",
            category="balance",
            widget="balance-electrico",
            start_date=start_date,
            end_date=end_date,
            time_trunc="day"
        )
        print("Successfully retrieved data:", data)
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving data: {e}") 