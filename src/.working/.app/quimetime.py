import json
import time

def stateful_generator(initial_state=None):
    """
    A stateful generator that can save its state to a file and regenerate itself.
    """
    if initial_state is None:
        state = {'counter': 0}
    else:
        state = initial_state

    while True:
        yield state
        state['counter'] += 1
        time.sleep(1)  

        if state['counter'] % 5 == 0:
            with open('generator_state.json', 'w') as f:
                json.dump(state, f)

            # Generate new code with the updated state - now with proper state handling
            with open('new_generator.py', 'w') as f:
                f.write(f"""
import json
import time

def stateful_generator(initial_state={state}):
    state = initial_state  # Properly initialize state from parameter
    while True:
        yield state
        state['counter'] += 1
        time.sleep(1)

if __name__ == '__main__':
    gen = stateful_generator()
    while True:
        try:
            state = next(gen)
            print(state)
        except StopIteration:
            break
                """)

if __name__ == '__main__':
    gen = stateful_generator()
    while True:
        try:
            state = next(gen)
            print(state)
        except StopIteration:
            break
