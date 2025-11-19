from functools import wraps
from time import perf_counter

class ComputationTracker:
    def __init__(self, cls):
        """Initialize with the target class to wrap and track."""
        self.cls = cls
        self.total_processed = 0
        self.tracked_methods = {}
        self.instance = None  # To store the instance once created

    def track_method(self, method):
        """Wraps a method to track execution time and processing rate with high precision."""
        @wraps(method)
        def wrapper(*args, **kwargs):
            # Start the precise timer
            start_time = perf_counter()
            # Call the actual method
            result = method(*args, **kwargs)
            # Calculate elapsed time
            elapsed_time = perf_counter() - start_time

            # Update total processed assuming result represents processing amount
            self.total_processed += result
            # Calculate processing rate
            processing_rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0

            # Display metrics
            print(f"⮑ Result: {result}")
            print(f"⮑ Time elapsed: {elapsed_time:.6f}s")
            print(f"⮑ Processing rate: {processing_rate:.2f} units/second")

            return result
        return wrapper

    def __call__(self, *args, **kwargs):
        """Create a wrapped instance of the class if not already done."""
        if self.instance is None:
            # Instantiate the target class
            self.instance = self.cls(*args, **kwargs)
            # Wrap all callable methods dynamically
            for name in dir(self.instance):
                if not name.startswith('_'):
                    attr = getattr(self.instance, name)
                    if callable(attr):
                        setattr(self.instance, name, self.track_method(attr))
        return self.instance

@ComputationTracker
class InferenceModel:
    def process(self, input_size):
        """Simulate a workload by incrementing a counter."""
        result = 0
        for _ in range(input_size):
            result += 1
        return result

def main():
    # Instantiate the model and run test cases
    model = InferenceModel()
    test_inputs = [40, 400, 400_000, 4_000_000, 40_000_000, 400_000_000]

    print("\n🕒 High Precision Computation Tracking Demonstration")
    print("=" * 50)

    for input_size in test_inputs:
        print(f"📊 Test: Processing input size {input_size}")
        model.process(input_size)

if __name__ == "__main__":
    main()
