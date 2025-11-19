from functools import wraps
from time import perf_counter

class ComputationTracker:
    def __init__(self, cls):
        self.cls = cls
        self.total_processed = 0
        self.tracked_methods = {}
        # Create an instance of the decorated class
        self.instance = None

    def track_method(self, method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            start_time = perf_counter()
            result = method(*args, **kwargs)
            elapsed_time = perf_counter() - start_time

            self.total_processed += result
            processing_rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0

            print(f"⮑ Result: {result}")
            print(f"⮑ Time elapsed: {elapsed_time:.6f}s")
            print(f"⮑ Processing rate: {processing_rate:.2f} units/second")

            return result
        return wrapper

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.cls(*args, **kwargs)
            # Wrap all methods of the instance
            for name in dir(self.instance):
                if not name.startswith('_'):
                    attr = getattr(self.instance, name)
                    if callable(attr):
                        setattr(self.instance, name, self.track_method(attr))
        return self.instance

@ComputationTracker
class InferenceModel:
    def process(self, input_size):
        # Adding some artificial workload
        result = 0
        for _ in range(input_size):
            result += 1
        return result

def main():
    model = InferenceModel()

    test_inputs = [40, 400, 400_000, 4_000_000, 40_000_000, 400_000_000]

    print("\n🕒 Computation Tracking Demonstration")
    print("=" * 50)

    for input_size in test_inputs:
        print(f"📊 Test: Processing input size {input_size}")
        model.process(input_size)

if __name__ == "__main__":
    main()
