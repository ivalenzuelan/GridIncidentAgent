import sqlite3
from datetime import datetime
import pandas as pd
from typing import List, Dict, Optional, Tuple
import os
from models import Outage

class OutageManager:
    """Manages mock outages using SQLite database."""
    
    def __init__(self, db_path: str = "mock_outages.db", csv_path: str = "mock_outages.csv"):
        """
        Initialize the outage manager.
        
        Args:
            db_path: Path to the SQLite database file
            csv_path: Path to the CSV file containing outage data
        """
        self.db_path = db_path
        self._init_db()
        self.df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        # Ensure 'resolved' and 'resolved_time' columns exist
        if 'resolved' not in self.df.columns:
            self.df['resolved'] = False
        if 'resolved_time' not in self.df.columns:
            self.df['resolved_time'] = pd.NaT
    
    def _init_db(self) -> None:
        """Initialize the SQLite database with the required schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    station_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    duration_min INTEGER NOT NULL,
                    crew_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def load_from_csv(self, csv_path: str) -> None:
        """
        Load outages from a CSV file into the database.
        
        Args:
            csv_path: Path to the CSV file containing outage data
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        required_columns = ['timestamp', 'station_id', 'type', 'duration_min']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"CSV must contain columns: {required_columns}")
        
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql('outages', conn, if_exists='append', index=False)
    
    def get_active_outages(self, end_time: datetime) -> List[Outage]:
        # Outages that started before end_time and have not ended yet
        active = self.df[(self.df["timestamp"] <= end_time) & (self.df["resolved"] == False)]
        return [Outage(**row) for row in active.to_dict(orient="records")]

    def get_resolved_outages(self, start_time: datetime, end_time: datetime) -> List[Outage]:
        # Outages resolved within the window
        resolved = self.df[(self.df["resolved"] == True) & (self.df["resolved_time"] >= start_time) & (self.df["resolved_time"] <= end_time)]
        return [Outage(**row) for row in resolved.to_dict(orient="records")]

    def get_outages(self, start_time: datetime, end_time: datetime) -> Tuple[List[Outage], List[Outage]]:
        """Return (active_outages, resolved_outages) for the given time window."""
        active = self.get_active_outages(end_time)
        resolved = self.get_resolved_outages(start_time, end_time)
        return active, resolved
    
    def get_outages_by_station(self, station_id: str) -> List[Dict]:
        """
        Get all outages for a specific station.
        
        Args:
            station_id: ID of the station to query
            
        Returns:
            List of outage records for the station
        """
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM outages WHERE station_id = ? ORDER BY timestamp DESC"
            cursor = conn.execute(query, (station_id,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_outages_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        Get outages within a specific time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List of outage records within the time range
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM outages 
                WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
                ORDER BY timestamp DESC
            """
            cursor = conn.execute(query, (start_time, end_time))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Example usage:
if __name__ == "__main__":
    # Create sample CSV file
    sample_data = pd.DataFrame({
        'timestamp': [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            (datetime.now() - pd.Timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        ],
        'station_id': ['STN001', 'STN002'],
        'type': ['transformer', 'line'],
        'duration_min': [120, 60],
        'crew_notes': ['Transformer overheating', 'Line fault'],
        'resolved': [False, True],
        'resolved_time': [pd.NaT, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    })
    sample_data.to_csv('mock_outages.csv', index=False)
    
    # Initialize outage manager and load data
    manager = OutageManager()
    manager.load_from_csv('mock_outages.csv')
    
    # Query active outages
    active_outages = manager.get_active_outages(datetime.now())
    print("Active outages:", active_outages)
    
    # Query outages by station
    station_outages = manager.get_outages_by_station('STN001')
    print("\nOutages for STN001:", station_outages)

    # Query outages for a specific time range
    start_time = datetime.now() - pd.Timedelta(hours=2)
    end_time = datetime.now() + pd.Timedelta(hours=2)
    active, resolved = manager.get_outages(start_time, end_time)
    print("\nActive outages:", active)
    print("\nResolved outages:", resolved) 