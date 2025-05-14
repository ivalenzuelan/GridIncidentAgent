# Grid Incident Agent

A sophisticated agent for monitoring and reporting on electrical grid performance, with real-time analysis and AI-powered executive summaries.

## Architecture Overview

The Grid Incident Agent is built with a modular architecture that combines grid simulation, outage management, weather monitoring, and AI-powered analysis. Here's a detailed breakdown of its components:

### Core Components

1. **GridAgent** (`grid_agent.py`)
   - Main orchestrator class that coordinates all subsystems
   - Handles async data collection and report generation
   - Manages AI-powered executive summaries via Cloudflare Workers AI
   - Implements context managers for resource management

2. **GridSimulator** (`grid_simulator.py`)
   - Simulates power flow analysis using PYPOWER
   - Provides voltage measurements and grid state data
   - Handles 39-bus test system simulation
   - Generates realistic grid measurements with noise

3. **OutageManager** (`outage_manager.py`)
   - Tracks active and resolved outages
   - Manages outage data persistence
   - Provides outage statistics and filtering
   - Handles outage deduplication

4. **AEMETClient** (`aemet_client.py`)
   - Weather data client for Spanish grid locations
   - Provides temperature, humidity, and conditions
   - Supports multiple locations (Madrid, Barcelona)
   - Includes mock data for testing

### Data Models

1. **GridReport** (`models.py`)
   - Comprehensive report structure
   - Includes voltage statistics, outages, weather
   - Contains alerts and recommendations
   - Optional AI-generated executive summary

2. **GridMeasurement**
   - Voltage magnitude and angle measurements
   - Timestamp and bus identification
   - Used for grid state analysis

3. **Outage**
   - Station identification
   - Outage type and duration
   - Resolution status and timing

4. **WeatherData**
   - Location-specific weather information
   - Temperature, humidity, conditions
   - Timestamp for temporal analysis

### Key Features

1. **Real-time Monitoring**
   - 5-minute measurement intervals
   - Voltage level tracking
   - Outage detection and tracking
   - Weather condition monitoring

2. **Intelligent Analysis**
   - Voltage threshold monitoring
   - Outage impact assessment
   - Weather correlation analysis
   - Automated alert generation

3. **AI-Powered Reporting**
   - Executive summary generation
   - Impact analysis
   - Root cause identification
   - Action recommendations

4. **Configurable Parameters**
   - Voltage thresholds via environment variables
   - Time range customization
   - Location-specific monitoring
   - API credentials management

### Data Flow

1. **Data Collection**
   ```
   GridAgent
   ├── GridSimulator (voltage measurements)
   ├── OutageManager (outage status)
   └── AEMETClient (weather data)
   ```

2. **Analysis Pipeline**
   ```
   Raw Data → Voltage Analysis → Outage Analysis → Weather Correlation → Alert Generation
   ```

3. **Report Generation**
   ```
   Analysis Results → GridReport Creation → AI Summary → Final Report
   ```

### Environment Configuration

Required environment variables:
- `VOLT_LIMIT_CRITICAL_LOW`: Critical low voltage threshold
- `VOLT_LIMIT_CRITICAL_HIGH`: Critical high voltage threshold
- `VOLT_LIMIT_DEGRADED_LOW`: Degraded low voltage threshold
- `VOLT_LIMIT_DEGRADED_HIGH`: Degraded high voltage threshold
- `CF_ACCOUNT_ID`: Cloudflare account ID for AI features
- `CF_API_TOKEN`: Cloudflare API token for AI features

### Testing

The system includes comprehensive tests in `test_grid_agent.py`:
1. 15-minute report generation
2. Executive summary verification
3. 30-minute extended report
4. Error handling and edge cases

### Dependencies

- Python 3.10+
- PYPOWER 5.1.18
- aiohttp
- numpy
- python-dotenv
- Cloudflare Workers AI API

## Usage Example

```python
async with GridAgent() as agent:
    report = await agent.generate_report(time_range_minutes=15)
    print(f"Grid Status: {report.grid_status}")
    print(f"Active Outages: {len(report.active_outages)}")
    if report.exec_summary:
        print("\nExecutive Summary:")
        print(report.exec_summary)
```

## Future Improvements

1. Enhanced outage correlation
2. Machine learning for predictive analysis
3. Real-time alert notifications
4. Historical data analysis
5. Custom report templates
6. Additional weather data sources
7. Grid topology visualization 