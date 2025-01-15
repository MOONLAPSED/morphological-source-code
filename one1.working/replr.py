import code
import operator
import sys
import argparse

class StateKernel(code.InteractiveConsole):
    """
    StateKernel is a subclass of InteractiveConsole that provides a custom REPL.
    
    This subclass builds on InteractiveInterpreter and adds prompting using the familiar
    sys.ps1 and sys.ps2, input buffering, and improved operator handling within the REPL environment.
    """
    OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
    }

    def __init__(self, locals=None, filename="<console>", local_exit=False):
        super().__init__(locals=locals, filename=filename)
        self.local_exit = local_exit

    def runcode(self, code_obj):
        try:
            exec(code_obj, self.locals)
        except SystemExit:
            if not self.local_exit:
                raise
            print("Exit attempted but local_exit is True. Returning to REPL.")
        except Exception as e:
            self.showtraceback()

    def showtraceback(self):
        type, value, tb = sys.exc_info()
        print(f"Exception of type {type.__name__} occurred with message: {value}")
        super().showtraceback()

    def showsyntaxerror(self, filename=None):
        super().showsyntaxerror(filename=filename)

    def interact(self, banner=None, exitmsg=None):
        if banner is None:
            banner = "Welcome to the StateKernel custom shell. Type exit() or quit() to exit."
        if exitmsg is None:
            exitmsg = "Goodbye from StateKernel!"
        super().interact(banner=banner, exitmsg=exitmsg)

    def push(self, line):
        try:
            tokens = line.split()
            if len(tokens) == 3 and tokens[1] in self.OPERATORS:
                operand1 = float(tokens[0])
                operand2 = float(tokens[2])
                operation = self.OPERATORS[tokens[1]]
                print(f"Result: {operation(operand1, operand2)}")
                return False
        except (ValueError, KeyError) as e:
            print(f"Invalid input or operation: {e}. Executing line normally.")
        return super().push(line)

class Interpreter:
    def __init__(self):
        self.commands = [
            "clear", "exit", "banner", "exec", "restart", "upgrade", 'search',
            "use auxiliary/gather/ip_gather", "use auxiliary/gather/ip_lookup",
            "use auxiliary/core/pyconverter", "use exploit/windows/ftp/ftpshell_overflow",
            "use exploit/android/login/login_bypass", "use exploit/windows/http/oracle9i_xdb_pass"
        ]

    def search_module(self, query):
        # Placeholder for actual search logic
        print(f"Searching for module: {query}")

    def handle_command(self, command):
        parser = argparse.ArgumentParser(description='PySploit Command Line Interface')
        subparsers = parser.add_subparsers(dest='command', required=True)

        # Define subparsers for each command
        subparsers.add_parser('clear', help='Clear the screen')
        subparsers.add_parser('exit', help='Exit the interpreter')
        subparsers.add_parser('banner', help='Show the banner')
        subparsers.add_parser('exec', help='Execute a Python expression')
        subparsers.add_parser('restart', help='Restart the interpreter')
        subparsers.add_parser('upgrade', help='Upgrade the interpreter')
        search_parser = subparsers.add_parser('search', help='Search for a module')
        search_parser.add_argument('query', help='The module to search for')

        args = parser.parse_args(command.split())

        if args.command == 'exit':
            print("Goodbye from PySploit!")
            sys.exit(0)
        elif args.command == 'search':
            self.search_module(args.query)
        else:
            print(f"Handling command: {args.command}")

    def start_interpreter(self):
        while True:
            try:
                main_ask = input("\033[4mPySploit\033[0m >> ").strip()
                if main_ask.lower() in ['exit', 'quit']:
                    print("Goodbye from PySploit!")
                    break
                else:
                    self.handle_command(main_ask)
            except (KeyboardInterrupt, EOFError):
                print('\nType exit to close the program\n')

if __name__ == "__main__":
    kernel = StateKernel()
    interpreter = Interpreter()
    interpreter.start_interpreter()