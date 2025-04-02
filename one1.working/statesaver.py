import json
import time
import os
import inspect


def stateful_generator(initial_state=None, filename='generator_state.json', new_filename='new_generator.py'):
    """
    A generator that maintains state, saves it to a file, and can self-replicate.

    Args:
        initial_state (dict, optional): The initial state of the generator. Defaults to None.
        filename (str, optional): The name of the file to save the state to. Defaults to 'generator_state.json'.
        new_filename (str, optional): The name of the file to write the new generator code to. Defaults to 'new_generator.py'.

    Yields:
        dict: The current state of the generator.
    """
    if initial_state is None:
        state = {'counter': 0, 'message': "Initial State"}
    else:
        state = initial_state

    while True:
        yield state
        state['counter'] += 1
        time.sleep(1)  # Simulate some work
        # Check for a condition to trigger state saving and self-replication
        if state['counter'] % 5 == 0:
            _save_state(state, filename)
            _generate_new_code(state, filename, new_filename)
            # Optionally, trigger a restart or exit the current process.  This depends on your OS and environment.
            # For a true "rebirth", you would likely need to have a separate process monitor for the new file
            # and then relaunch the script.
            # os._exit(0)  # Example: Exits the current process.
            print("Generator finished.  Waiting for rebirth.")
            os._exit(0)  # Requires an external process to monitor and restart

def _save_state(state, filename):
    """Saves the generator's state to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(state, f, indent=4) # Added indent for readability
        print(f"State saved to {filename}: {state}")
    except Exception as e:
        print(f"Error saving state: {e}")

def _generate_new_code(state, filename, new_filename):
    """Generates new code, including imports and correct module reference."""
    try:
        current_source = inspect.getsource(stateful_generator)
        # Get the name of the current module (e.g., 'statesaver')
        current_module = inspect.getmodule(stateful_generator).__name__
        # Add imports and correct module reference to the generated code
        imports = f"""
import json
import time
import os
import inspect
import importlib
from {current_module} import stateful_generator  # Import from the original module
"""

        new_source = f"{imports}\n{current_source.replace('initial_state=None', f'initial_state={state}')}"

        with open(new_filename, 'w') as f:
            f.write(new_source)
        print(f"New generator code written to {new_filename}")

    except Exception as e:
        print(f"Error generating new code: {e}")

# Subsequent runs (after the new code is generated):
# You would need a separate mechanism to detect the "new_generator.py" file
# and then execute it.  This is OS-dependent.  Here's a highly simplified example:

# First run (in statesaver.py):
gen = stateful_generator()
for _ in range(10):  # Run for a while
    try:
        state = next(gen)
        print(state)
    except StopIteration:
        break

# if os.path.exists('new_generator.py'):
#    import new_generator  # This would dynamically import the new code
#    gen2 = new_generator.stateful_generator()
#    # ... continue processing with gen2 ...
#    for _ in range(10):  # Run for a while
#         try:
#            state = next(gen2)
#            print(state)
#         except StopIteration:
#            break

# "Rebirth" (Requires an external trigger - e.g., run_new_generator.py)

# In a separate script (e.g., run_new_generator.py) after the first run:
# import os
# import importlib
# from pathlib import Path
# from importlib  import util
# 
# new_filename = 'new_generator.py'
# 
# if os.path.exists(new_filename):
#     module_name = 'new_generator'  # No .py extension
#     spec = importlib.util.spec_from_file_location(module_name, new_filename)
#     module = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(module)
# 
#     gen2 = module.stateful_generator()  # Call the generator from the dynamically loaded module
#     for _ in range(5):  # Example: Run the new generator for a few iterations
#         try:
#             state = next(gen2)
#             print(state)
#         except StopIteration:
#             break