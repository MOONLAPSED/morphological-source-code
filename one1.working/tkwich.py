import sys
import tkinter as tk
import code
import atexit
import threading
import queue


class REPLConsole(code.InteractiveConsole):
    """Interactive Python console for Tkinter."""

    def __init__(self, output_widget):
        super().__init__()
        self.output_widget = output_widget
        self.locals = {}

    def write(self, data):
        """Redirect output to Tkinter widget."""
        self.output_widget.insert("end", data)
        self.output_widget.see("end")

    def run_command(self, command):
        """Execute user input inside REPL."""
        self.push(command + "\n")  # Simulate pressing Enter


class TkinterREPL:
    def __init__(self, root):
        self.root = root
        self.root.title("Python StdLib REPL")

        # Text widget for output
        self.output = tk.Text(root, wrap="word", height=20, width=80)
        self.output.pack(expand=True, fill="both")
        self.output.insert("end", ">>> ")  # Initial prompt

        # Input capture (hidden, Tkinter handles input in the main text widget)
        self.input_queue = queue.Queue()
        self.console = REPLConsole(self.output)

        # Key bindings
        self.output.bind("<Return>", self.enter_pressed)

        # Redirect stdout/stderr
        sys.stdout = self.console
        sys.stderr = self.console

        # Start a thread for REPL execution
        self.repl_thread = threading.Thread(target=self.run_repl, daemon=True)
        self.repl_thread.start()

    def enter_pressed(self, event):
        """Capture user input when Enter is pressed."""
        input_text = self.output.get("end-2l", "end-1c")  # Last entered line
        self.output.insert("end", "\n")  # Move to the next line
        self.output.see("end")

        # Store input for execution
        self.input_queue.put(input_text.strip())
        return "break"  # Prevent default Enter behavior

    def run_repl(self):
        """Background REPL loop to process user input."""
        while True:
            command = self.input_queue.get()  # Wait for input
            if command.lower() in {"exit()", "quit()"}:
                self.root.quit()
                break
            self.console.run_command(command)  # Execute in REPL


def start_repl():
    """Create and start the REPL window."""
    root = tk.Tk()
    app = TkinterREPL(root)
    root.mainloop()


if __name__ == "__main__":
    start_repl()
