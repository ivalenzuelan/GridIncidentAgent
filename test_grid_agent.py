import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from grid_agent import GridAgent
from typing import Dict, List

async def test_grid_agent():
    """Test the grid agent functionality."""
    print("Starting Grid Agent Test...")
    print("--------------------------------------------------")
    
    # Test 1: Generate a 15-minute report
    print("\nTest 1: Generating 15-minute report...")
    async with GridAgent() as agent:
        report = await agent.generate_report(time_range_minutes=15)
        
        print("\nGrid Status:", report.grid_status)
        print("\nVoltage Statistics:")
        for stat, value in report.voltage_stats.items():
            print(f"  {stat}: {value:.3f}")
            
        print("\nActive Outages:", len(report.active_outages))
        for outage in report.active_outages:
            print(f"  - {outage.station_id}: {outage.type} (Duration: {outage.duration_min} min)")
        
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
    
    # Test 2: Check if executive summary was generated
    print("\nTest 2: Checking executive summary...")
    if not os.getenv("CF_ACCOUNT_ID") or not os.getenv("CF_API_TOKEN"):
        print("Cloudflare credentials not configured - skipping executive summary test")
    else:
        async with GridAgent() as agent:
            report = await agent.generate_report(time_range_minutes=15)
            if report.exec_summary:
                print("\nExecutive Summary:")
                print("--------------------------------------------------")
                print(report.exec_summary)
            else:
                print("No executive summary generated")
    
    # Test 3: Generate a 30-minute report
    print("\nTest 3: Generating 30-minute report...")
    async with GridAgent() as agent:
        report = await agent.generate_report(time_range_minutes=30)
        print(f"Status: {report.grid_status}")
        print(f"Active Outages: {len(report.active_outages)}")
        print(f"Resolved Outages: {len(report.resolved_outages)}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["CF_ACCOUNT_ID", "CF_API_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Warning: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file to enable the executive summary feature.")
    
    # Run the tests
    asyncio.run(test_grid_agent()) 