import select
import sys
from typing import Optional, Dict

class Charqueue:
    """A simple queue data structure for managing characters."""
    
    def __init__(self) -> None:
        """Initialize an empty character queue."""
        self.queue: list[str] = []

    def add(self, char: str) -> None:
        """Add a character to the queue."""
        self.queue.append(char)

    def get(self) -> str:
        """Remove and return the first character from the queue."""
        return self.queue.pop(0)

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return not self.queue

    def clear(self) -> None:
        """Clear all characters from the queue."""
        self.queue.clear()

def pop_charqueue(char_queue: Charqueue) -> str:
    """Process the character queue and return the result as a single string."""
    result = ""
    while not char_queue.empty():
        char = char_queue.get()
        if char.isspace():
            result += " "
        elif char.strip():
            result += char
    return result

# Key sequences for navigation and control
ARROW_UP = '\x1b[A'
ARROW_DOWN = '\x1b[B'
ARROW_RIGHT = '\x1b[C'
ARROW_LEFT = '\x1b[D'
CTRL_C = '\x03'

def handle_arrow_key(key: str) -> None:
    """Handle logic when an arrow key is pressed."""
    directions = {
        ARROW_UP: "Up arrow pressed.",
        ARROW_DOWN: "Down arrow pressed.",
        ARROW_LEFT: "Left arrow pressed.",
        ARROW_RIGHT: "Right arrow pressed."
    }
    print(directions.get(key, "Unknown key pressed."))

class REPL:
    def __init__(self) -> None:
        self.running: bool = True
        self.state: Dict[str, str] = {}

    def read(self) -> Optional[str]:
        """Read input from the user, non-blocking."""
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if ready:
            return sys.stdin.read().strip()
        return None

    def evaluate(self, command: str) -> None:
        """Process the given command."""
        if command == 'quit':
            self.running = False
        elif command.startswith('print '):
            _, expr = command.split(maxsplit=1)
            self.output(f"Command Result: {expr}")
        else:
            self.output("Unrecognized command")

    def output(self, message: str) -> None:
        """Output a message to the user."""
        print(message)

    def loop(self) -> None:
        """Run the REPL loop."""
        self.output("Welcome to the interactive REPL. Type 'quit' to exit.")
        while self.running:
            command = self.read()
            if command:
                self.evaluate(command)
            # Add other processing that doesn't depend on user input here

def setup_environment() -> None:
    """Perform any necessary environment setup before beginning the REPL."""
    print("Setting up environment...")

def handle_input() -> None:
    """Handle extended input including arrow key presses."""
    char_queue = Charqueue()
    qqueue = ""
    pqueue = ""

    print("Processing input. Press Ctrl+C to exit.")
    try:
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                char = sys.stdin.read(1)
                if char == '\x1b':
                    char += sys.stdin.read(2)
                    if char in (ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT):
                        handle_arrow_key(char)
                elif char == CTRL_C:
                    print("\nExiting input handler.")
                    break
                elif char == '\n' or char in ["'", '"', '\\']:
                    continue
                else:
                    char_queue.add(char)
                    pc = pop_charqueue(char_queue).rstrip()
                    qqueue += pc
                    print(pc, end="", flush=True)
            elif qqueue:
                print(qqueue)
                pqueue += qqueue
                qqueue = ""
    except KeyboardInterrupt:
        print("\nInput processing interrupted by user.")
class GameWorld:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.map = [[' ' for _ in range(width)] for _ in range(height)]
        self.player_position = [0, 0]  # Starting point (0,0)

    def move_player(self, direction):
        x, y = self.player_position
        if direction == 'up' and x > 0:
            self.player_position[0] -= 1
        elif direction == 'down' and x < self.height - 1:
            self.player_position[0] += 1
        elif direction == 'left' and y > 0:
            self.player_position[1] -= 1
        elif direction == 'right' and y < self.width - 1:
            self.player_position[1] += 1

    def render(self):
        x, y = self.player_position
        view = [row[:] for row in self.map]
        view[x][y] = 'P'  # P for Player
        for row in view:
            print(''.join(row))
        print("\nUse arrow keys to move. Type 'quit' to exit.")

def main_game_loop():
    game_world = GameWorld(width=10, height=10)
    repl = REPL()

    try:
        while repl.running:
            command = repl.read()

            if command:
                if command.startswith('\x1b'):  # Escape sequence start
                    if command == ARROW_UP:
                        game_world.move_player('up')
                    elif command == ARROW_DOWN:
                        game_world.move_player('down')
                    elif command == ARROW_LEFT:
                        game_world.move_player('left')
                    elif command == ARROW_RIGHT:
                        game_world.move_player('right')
                elif command == 'quit':
                    repl.running = False
                else:
                    repl.evaluate(command)

            game_world.render()

    except KeyboardInterrupt:
        repl.output("\nExiting REPL gracefully.")

def main() -> None:
    """Perform setup, run REPL, and handle input."""
    setup_environment()
    repl = REPL()
    try:
        repl.loop()
    except KeyboardInterrupt:
        repl.output("\nExiting REPL gracefully.")

    handle_input()

if __name__ == "__main__":
    main()
    main_game_loop()