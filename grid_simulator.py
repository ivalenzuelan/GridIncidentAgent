import numpy as np
from datetime import datetime, timedelta
import pypower.api as pp
from typing import Dict, List, Tuple, Optional
import random

class GridSimulator:
    """High-frequency grid simulator using PyPower with IEEE 39-bus model."""
    
    def __init__(self, sampling_rate: float = 50.0):
        """
        Initialize the grid simulator.
        
        Args:
            sampling_rate: Sampling rate in Hz (default: 50 Hz)
        """
        self.sampling_rate = sampling_rate
        self.time_step = 1.0 / sampling_rate
        self.current_time = datetime.now()
        
        # Initialize IEEE 39-bus case
        self.case = pp.case39()
        self.ppc = pp.runpf(self.case)[0]
        
        # Initialize state variables
        self.bus_count = self.ppc['bus'].shape[0]
        self.voltage_magnitudes = self.ppc['bus'][:, 7]  # Initial voltage magnitudes
        self.voltage_angles = self.ppc['bus'][:, 8]      # Initial voltage angles
        
        # Fault injection parameters
        self.fault_probability = 0.001  # Probability of fault per time step
        self.fault_duration = timedelta(seconds=0.1)  # Fault duration
        self.active_faults: List[Tuple[int, datetime]] = []  # (bus_id, end_time)
    
    def inject_fault(self, bus_id: int) -> None:
        """
        Inject a fault at a specific bus.
        
        Args:
            bus_id: Bus ID where to inject the fault
        """
        if 0 <= bus_id < self.bus_count:
            end_time = self.current_time + self.fault_duration
            self.active_faults.append((bus_id, end_time))
            # Simulate fault by reducing voltage magnitude
            self.voltage_magnitudes[bus_id] *= 0.5
    
    def update_state(self) -> None:
        """Update the grid state for the next time step."""
        # Update time
        self.current_time += timedelta(seconds=self.time_step)
        
        # Check for random fault injection
        if random.random() < self.fault_probability:
            bus_id = random.randint(0, self.bus_count - 1)
            self.inject_fault(bus_id)
        
        # Clear expired faults
        self.active_faults = [(bus_id, end_time) for bus_id, end_time in self.active_faults 
                            if end_time > self.current_time]
        
        # Update voltage magnitudes and angles with small random variations
        self.voltage_magnitudes += np.random.normal(0, 0.001, self.bus_count)
        self.voltage_angles += np.random.normal(0, 0.01, self.bus_count)
        
        # Ensure voltage magnitudes stay within reasonable bounds
        np.clip(self.voltage_magnitudes, 0.9, 1.1, out=self.voltage_magnitudes)
    
    def get_measurements(self) -> Dict[str, np.ndarray]:
        """
        Get current grid measurements.
        
        Returns:
            Dict containing voltage magnitudes and angles
        """
        return {
            'timestamp': self.current_time,
            'voltage_magnitudes': self.voltage_magnitudes.copy(),
            'voltage_angles': self.voltage_angles.copy(),
            'active_faults': [bus_id for bus_id, _ in self.active_faults]
        }

    def get_voltage_measurements(self) -> Dict[int, Tuple[float, float]]:
        """Get current voltage measurements for all buses.
        
        Returns:
            Dict mapping bus IDs to (magnitude, angle) tuples.
            Magnitude is in per-unit (p.u.), angle in degrees.
        """
        # Simulate voltage measurements with some noise
        measurements = {}
        for bus_id in range(self.bus_count):
            # Base voltage around 1.0 p.u. with some variation
            magnitude = 1.0 + np.random.normal(0, 0.02)
            # Angle between -15 and 15 degrees
            angle = np.random.uniform(-15, 15)
            measurements[bus_id] = (magnitude, angle)
        return measurements

# Example usage:
if __name__ == "__main__":
    simulator = GridSimulator()
    
    # Simulate for 1 second
    for _ in range(50):  # 50 Hz = 50 samples per second
        simulator.update_state()
        measurements = simulator.get_measurements()
        print(f"Time: {measurements['timestamp']}")
        print(f"Active faults: {measurements['active_faults']}")
        print(f"Bus 1 voltage: {measurements['voltage_magnitudes'][0]:.3f} pu")
        print("---") 