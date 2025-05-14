from __future__ import annotations

"""GridAgent – mock grid‑performance reporting agent with LLM summary.

This version includes the fixes discussed:
    • Async‑safe data fetch using ``asyncio.to_thread``
    • Parametrised voltage thresholds via environment variables
    • Uses ``current_time`` in measurement loop
    • Optional LLM‑powered executive summary using Cloudflare Workers AI API
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import os
from dotenv import load_dotenv
import numpy as np
import aiohttp
import json
import contextlib
import io
import sys

# Third‑party / internal modules
from models import GridReport, GridMeasurement, Outage, WeatherData  # type: ignore
from grid_simulator import GridSimulator  # type: ignore
from outage_manager import OutageManager  # type: ignore
from aemet_client import AEMETClient  # type: ignore

# Load env first so thresholds / keys are available
load_dotenv()

# ─────────────────────────────────────────── constants & helpers ──

# Voltage limits (pu) – configurable via env or default values
VOLT_LIMIT_CRITICAL_LOW = float(os.getenv("VOLT_LIMIT_CRITICAL_LOW", "0.95"))
VOLT_LIMIT_CRITICAL_HIGH = float(os.getenv("VOLT_LIMIT_CRITICAL_HIGH", "1.05"))
VOLT_LIMIT_DEGRADED_LOW = float(os.getenv("VOLT_LIMIT_DEGRADED_LOW", "0.97"))
VOLT_LIMIT_DEGRADED_HIGH = float(os.getenv("VOLT_LIMIT_DEGRADED_HIGH", "1.03"))

# Cloudflare Workers AI API configuration
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_MODEL = "@cf/meta/llama-2-7b-chat-int8"  # Using Llama 2 model
CF_API_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"

# Base prompt for executive summary
SUMMARY_PROMPT = (
    "You are a senior grid‑control engineer. Summarise the grid report "
    "in exactly **5 concise bullets** (no greetings or closings). "
    "Use the helper vars: v_min={v_min}, v_max={v_max}, active_outages={num_active}. "
    "Focus on impact, root‑cause, next actions.\n\nJSON:\n{report_json}"
)

# ────────────────────────────────────────────── main agent class ──

class GridAgent:
    """Agent for monitoring and reporting on electrical grid performance."""
    
    def __init__(self):
        """Initialize the grid agent with required components."""
        self.grid_simulator = GridSimulator()
        self.outage_manager = OutageManager()
        self.weather_client = AEMETClient()
        self.session = None
        
    async def __aenter__(self):
        """Set up async resources."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async resources."""
        if self.session:
            await self.session.close()
            
    async def fetch_grid_data(self, start_time: datetime, end_time: datetime) -> List[GridMeasurement]:
        """Fetch grid measurements for the specified time range."""
        measurements = []
        current_time = start_time
        
        while current_time <= end_time:
            # Get voltage measurements from grid simulator
            voltages = self.grid_simulator.get_voltage_measurements()
            
            for bus_id, (magnitude, angle) in voltages.items():
                measurements.append(GridMeasurement(
                    timestamp=current_time,
                    voltage_magnitude=magnitude,
                    voltage_angle=angle,
                    bus_id=bus_id
                ))
            
            current_time += timedelta(minutes=5)  # 5-minute intervals
            
        return measurements
        
    async def fetch_outages(self, start_time: datetime, end_time: datetime) -> Dict[str, List[Outage]]:
        """Fetch active and resolved outages for the specified time range."""
        active = self.outage_manager.get_active_outages(end_time)
        resolved = self.outage_manager.get_resolved_outages(start_time, end_time)
        
        return {
            "active": active,  # Already a list of Outage objects
            "resolved": resolved  # Already a list of Outage objects
        }
        
    async def fetch_weather(self, locations: List[str]) -> List[WeatherData]:
        """Fetch weather data for specified locations."""
        weather_data = []
        obs_func = self.weather_client.get_observations
        
        for location in locations:
            # Vary mock temperature based on location
            observations = await asyncio.to_thread(obs_func, location)
            if "temperature" not in observations:
                base = 21.0 if location == "Madrid" else 23.0
                observations["temperature"] = base + np.random.normal(0, 1)
                
            weather_data.append(WeatherData(
                location=location,
                timestamp=datetime.now(),
                temperature=observations["temperature"],
                humidity=observations["humidity"],
                wind_speed=observations["wind_speed"],
                precipitation=observations["precipitation"],
                conditions=observations["conditions"]
            ))
        return weather_data
        
    def analyze_grid_status(self, measurements: List[GridMeasurement], outages: Dict[str, List[Outage]]) -> Tuple[str, List[str], List[str]]:
        """Analyze grid measurements to determine status, alerts, and recommendations."""
        # Calculate voltage statistics
        magnitudes = [m.voltage_magnitude for m in measurements]
        min_voltage = min(magnitudes)
        max_voltage = max(magnitudes)
        avg_voltage = sum(magnitudes) / len(magnitudes)
        
        # Determine grid status
        if min_voltage < VOLT_LIMIT_CRITICAL_LOW or max_voltage > VOLT_LIMIT_CRITICAL_HIGH:
            status = "critical"
        elif min_voltage < VOLT_LIMIT_DEGRADED_LOW or max_voltage > VOLT_LIMIT_DEGRADED_HIGH:
            status = "degraded"
        else:
            status = "normal"
            
        # Generate alerts and recommendations
        alerts = []
        recommendations = []
        
        # Deduplicate and count active outages
        unique_active = {(o.station_id, o.type) for o in outages["active"]}
        num_active = len(unique_active)
        if num_active:
            alerts.append(f"{num_active} active outages")
            recommendations.append("Prioritise restoration for affected substations")
        
        if status == "critical":
            alerts.append("Critical voltage levels detected")
            recommendations.append("Immediate action required to stabilise voltage levels")
        elif status == "degraded":
            alerts.append("Voltage levels outside normal range")
            recommendations.append("Monitor voltage levels and prepare for potential corrective action")
            
        return status, alerts, recommendations
        
    async def narrative_summary(self, report: GridReport) -> Optional[str]:
        """Generate an executive summary using Cloudflare Workers AI."""
        if not CF_ACCOUNT_ID or not CF_API_TOKEN:
            print("Cloudflare credentials not configured - skipping executive summary")
            return None
            
        try:
            # Calculate key metrics
            vmin = report.voltage_stats["min"]
            vmax = report.voltage_stats["max"]
            num_out = len({(o.station_id, o.type) for o in report.active_outages})
            
            # Create a concise JSON payload
            concise_report = {
                "status": report.grid_status,
                "voltage": {
                    "min": f"{vmin:.3f}",
                    "max": f"{vmax:.3f}",
                    "avg": f"{report.voltage_stats['avg']:.3f}"
                },
                "outages": {
                    "active": num_out,
                    "resolved": len(report.resolved_outages)
                },
                "weather": [f"{w.location}: {w.conditions}" for w in report.weather_data],
                "alerts": report.alerts,
                "actions": report.recommendations
            }
            
            # Prepare the prompt with context metrics
            prompt = SUMMARY_PROMPT.format(
                report_json=json.dumps(concise_report, indent=2),
                v_min=f"{vmin:.3f}",
                v_max=f"{vmax:.3f}",
                num_active=num_out
            )

            # Make the API request
            headers = {
                "Authorization": f"Bearer {CF_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": [
                    {"role": "system", "content": prompt}
                ]
            }
            
            async with self.session.post(CF_API_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result and "response" in result["result"]:
                        summary = result["result"]["response"].strip()
                        return summary or "(LLM produced empty summary)"
                    else:
                        print(f"Unexpected API response format: {result}")
                        return None
                else:
                    error_text = await response.text()
                    print(f"API error: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            print(f"Error generating executive summary: {str(e)}")
            return None
            
    async def generate_report(self, time_range_minutes: int = 30) -> GridReport:
        """Generate a comprehensive grid performance report."""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_range_minutes)
        
        # Fetch data
        measurements = await self.fetch_grid_data(start_time, end_time)
        outages = await self.fetch_outages(start_time, end_time)
        weather_data = await self.fetch_weather(["Madrid", "Barcelona"])
        
        # Calculate voltage statistics
        magnitudes = [m.voltage_magnitude for m in measurements]
        voltage_stats = {
            "min": min(magnitudes),
            "max": max(magnitudes),
            "avg": sum(magnitudes) / len(magnitudes),
            "std": (sum((x - sum(magnitudes)/len(magnitudes))**2 for x in magnitudes) / len(magnitudes))**0.5
        }
        
        # Analyze grid status
        status, alerts, recommendations = self.analyze_grid_status(measurements, outages)
        
        # Create report
        report = GridReport(
            report_time=datetime.now(),
            time_range_start=start_time,
            time_range_end=end_time,
            measurements=measurements,
            voltage_stats=voltage_stats,
            active_outages=outages["active"],
            resolved_outages=outages["resolved"],
            weather_data=weather_data,
            grid_status=status,
            alerts=alerts,
            recommendations=recommendations
        )
        
        # Generate executive summary if Cloudflare credentials are available
        if CF_ACCOUNT_ID and CF_API_TOKEN:
            report.exec_summary = await self.narrative_summary(report)
            
        return report

async def main():
    """Example usage of the GridAgent."""
    async with GridAgent() as agent:
        # Generate a report for the last 30 minutes
        report = await agent.generate_report()
        
        # Print report summary
        print("\nGrid Status:", report.grid_status)
        print("\nVoltage Statistics:")
        for stat, value in report.voltage_stats.items():
            print(f"  {stat}: {value:.3f}")
            
        print("\nActive Outages:", len(report.active_outages))
        print("\nWeather Data:")
        for weather in report.weather_data:
            print(f"  {weather.location}:")
            print(f"    Temperature: {weather.temperature}°C")
            print(f"    Conditions: {weather.conditions}")
            
        print("\nAlerts:")
        for alert in report.alerts:
            print(f"  - {alert}")
            
        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")
            
        if report.exec_summary:
            print("\nExecutive Summary:")
            print("--------------------------------------------------")
            print(report.exec_summary)

if __name__ == "__main__":
    asyncio.run(main())
