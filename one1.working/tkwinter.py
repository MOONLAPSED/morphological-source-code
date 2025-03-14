import tkinter as tk
import atexit
import os


class RPNEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("RPN-Enabled Python Editor")

        # Create text widget
        self.text = tk.Text(root, wrap='word', undo=True)
        self.text.pack(expand=1, fill='both')

        # Load last session
        self.history_file = os.path.expanduser("~/.rpn_editor_history.py")
        self.load_last_session()

        # Setup atexit hook to save on close
        atexit.register(self.save_session)

        # Keybinding for RPN evaluation
        self.root.bind("<Return>", self.evaluate_rpn)

    def load_last_session(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                self.text.insert("1.0", f.read())

    def save_session(self):
        with open(self.history_file, "w") as f:
            f.write(self.text.get("1.0", "end-1c"))

    def evaluate_rpn(self, event=None):
        """ Evaluates the last entered line as an RPN expression. """
        lines = self.text.get("1.0", "end-1c").split("\n")
        if not lines:
            return

        stack = []
        tokens = lines[-1].split()

        for token in tokens:
            if token.isdigit():
                stack.append(int(token))
            elif token in {"+", "-", "*", "/"} and len(stack) >= 2:
                b, a = stack.pop(), stack.pop()
                stack.append(eval(f"{a} {token} {b}"))
            elif token == "dup":
                stack.append(stack[-1])
            elif token == "swap":
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif token == "drop":
                stack.pop()

        result = " ".join(map(str, stack))
        self.text.insert("end", f"\n=> {result}\n")
        return "break"


if __name__ == "__main__":
    root = tk.Tk()
    app = RPNEditor(root)
    root.mainloop()
