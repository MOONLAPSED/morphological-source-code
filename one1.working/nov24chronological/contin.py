import json
import time

initial_state = []

def stateful_generator(initial_state=None):
    """
    A stateful generator that can save its state to a file and regenerate itself.

    Args:
        initial_state (dict, optional): The initial state of the generator. Defaults to None.
    """

    if initial_state is None:
        state = {'counter': 0}
    else:
        state = initial_state

    while True:
        yield state
        state['counter'] += 1
        time.sleep(1)  # Simulate some work

        # Check for a condition to trigger state saving and self-replication
        if state['counter'] % 5 == 0:
            with open('generator_state.json', 'w') as f:
                json.dump(state, f)

            # Generate new code with the updated state
            with open('new_generator.py', 'w') as f:
                f.write(f"""
import json
import time

def stateful_generator(initial_state={state}):
    while True:
        yield state
        state['counter'] += 1
        time.sleep(1)

# Main execution loop
gen = stateful_generator(initial_state={state})
while True:
    try:
        state = next(gen)
        print(state)
    except StopIteration:
        break
                """)

# Main execution loop
gen = stateful_generator(initial_state)
while True:
    try:
        state = next(gen)
        print(state)
    except StopIteration:
        break