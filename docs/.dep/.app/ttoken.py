class TimeSeries:
    def __init__(self, max_size=20000):
        self.header = {}  # Header dictionary for metadata
        self.data = []    # List to hold tick dictionaries
        self.max_size = max_size  # Maximum number of ticks to retain

    def add_tick(self, tick_data):
        # Add a new tick (dictionary) to the time series
        self.data.append(tick_data)
        
        # If we exceed the max size, perform garbage collection
        if len(self.data) > self.max_size:
            self.garbage_collect()

    def garbage_collect(self):
        # Keep only the most recent max_size entries
        self.data = self.data[-self.max_size:]

    def get_latest(self):
        # Return the latest tick data
        return self.data[-1] if self.data else None

    def get_all_ticks(self):
        # Return all tick data
        return self.data

# Example usage
time_series = TimeSeries()

# Simulate high-frequency operations
for i in range(25000):
    time_series.add_tick({'tick': i, 'value': i * 2})

# Check the size of the time series
print(f"Number of ticks stored: {len(time_series.get_all_ticks())}")
print(f"Latest tick: {time_series.get_latest()}")