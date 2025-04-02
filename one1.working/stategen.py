import json
import time
import os
import inspect
import importlib
import subprocess
from pathlib import Path
from importlib import reload, import_module, util

class StatefulGeneratorManager:
    def __init__(self, generator_function, state_filename='generator_state.json', new_code_filename='new_generator.py'):
        self.generator_function = generator_function
        self.state_filename = state_filename
        self.new_code_filename = new_code_filename
        self.state = None  # Will be loaded or initialized

    def initialize_state(self, initial_state=None):
        if os.path.exists(self.state_filename):
            try:
                with open(self.state_filename, 'r') as f:
                    self.state = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode state from {self.state_filename}. Using default initial state.")
                self.state = initial_state if initial_state else self._get_default_state() # Use default if file corrupt
        else:
            self.state = initial_state if initial_state else self._get_default_state()


    def _get_default_state(self):
        # Define the default state structure for your specific generator.
        # This is where you would place the initial state values as before.
        return {'counter': 0, 'message': "Initial State"}


    def run(self, iterations=10):
        self.initialize_state()  # Load or initialize state

        gen = self.generator_function(initial_state=self.state) # Pass state to generator

        for _ in range(iterations):
            try:
                state = next(gen)
                print(state)
                self.state = state  # Update the manager's state
            except StopIteration:
                break

            if self.should_replicate(state):
                self.save_state()
                self.generate_new_code()
                self.launch_new_process()
                os._exit(0)

    def should_replicate(self, state):
        # Define your replication logic based on the state.
        return state['counter'] % 5 == 0

    def save_state(self):
        try:
            with open(self.state_filename, 'w') as f:
                json.dump(self.state, f, indent=4)
            print(f"State saved to {self.state_filename}: {self.state}")
        except Exception as e:
            print(f"Error saving state: {e}")

    def generate_new_code(self):
        try:
            current_source = inspect.getsource(self.generator_function)
            current_module = inspect.getmodule(self.generator_function).__name__
            state_str = json.dumps(self.state)

            imports = f"""
import json
import time
import os
import inspect
import importlib
import subprocess
from pathlib import Path
from importlib import reload, import_module, util
from {current_module} import {self.generator_function.__name__} # Import the specific generator
"""

            new_source = f"""{imports}

{current_source.replace('initial_state=None', f'initial_state={state_str}')}

"""

            with open(self.new_code_filename, 'w') as f:
                f.write(new_source)
            print(f"New generator code written to {self.new_code_filename}")

        except Exception as e:
            print(f"Error generating new code: {e}")

    def launch_new_process(self):
        subprocess.Popen(['python', __file__, 'rebirth'])

    @staticmethod
    def rebirth(generator_function_name, state_filename, new_code_filename):
        if os.path.exists(new_code_filename):
            module_name = new_code_filename[:-3]
            spec = importlib.util.spec_from_file_location(module_name, new_code_filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            generator_function = getattr(module, generator_function_name)

            manager = StatefulGeneratorManager(generator_function, state_filename, new_code_filename)
            manager.run(5)  # Run with the same config


# Example usage (statesaver.py):

def my_generator(initial_state=None):  # Your specific generator function
    state = initial_state if initial_state else {'counter': 0, 'message': "Initial State"}

    while True:
        yield state
        state['counter'] += 1
        time.sleep(1)



if __name__ == "__main__":
    manager = StatefulGeneratorManager(my_generator) # Use your generator here
    if len(os.sys.argv) > 1 and os.sys.argv[1] == 'rebirth':
        # Get config from the saved state file.
        with open(manager.state_filename, 'r') as f:
            saved_state = json.load(f)
            # Recreate the manager using the same config
            manager = StatefulGeneratorManager(my_generator, manager.state_filename, manager.new_code_filename)
            manager.rebirth(my_generator.__name__, manager.state_filename, manager.new_code_filename)
    else:
        manager.run(10)