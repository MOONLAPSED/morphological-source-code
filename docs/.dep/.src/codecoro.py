import random

class CheatCodeGenerator:
    def __init__(self):
        # Define some cheat codes
        self.cheat_codes = {
            "UP_UP_DOWN_DOWN_LEFT_RIGHT_LEFT_RIGHT_BA": "Access Granted!",
            "ALL_YOUR_BASE_ARE_BELONG_TO_US": "Welcome, Commander!",
            "ITS_A_TRAP": "You have been trapped!",
        }
        self.state = None  # Placeholder for state
        self.current_user = None

    def authenticate(self, code):
        """Validate the cheat code."""
        return self.cheat_codes.get(code)

    def generator(self):
        """A stateful generator that can accept cheat codes."""
        while True:
            if self.state is None:
                self.state = "waiting for authentication"
                print("Generator is ready. Please enter a cheat code:")
            
            # Wait for a cheat code input
            code = yield self.state
            
            # Validate the cheat code
            response = self.authenticate(code)
            if response:
                self.state = response
                print(f"Cheat code accepted: {response}")
            else:
                self.state = "Invalid code. Try again."
                print(self.state)

    def run(self):
        """Run the generator."""
        gen = self.generator()
        next(gen)  # Initialize the generator

        # Simulating external actors providing cheat codes
        cheat_codes_to_test = [
            "UP_UP_DOWN_DOWN_LEFT_RIGHT_LEFT_RIGHT_BA",
            "INVALID_CODE",
            "ALL_YOUR_BASE_ARE_BELONG_TO_US",
            "ITS_A_TRAP"
        ]

        for code in cheat_codes_to_test:
            print(f"Sending cheat code: {code}")
            response = gen.send(code)  # Send cheat code to generator

        # Resetting the generator to a new state
        print("Resetting generator...")
        gen.close()  # Close the old generator
        gen = self.generator()  # Create a new generator
        next(gen)  # Initialize the new generator
        print("Generator reset. Please enter a new cheat code:")

        # Testing the new generator
        new_cheat_codes = [
            "ALL_YOUR_BASE_ARE_BELONG_TO_US",
            "UP_UP_DOWN_DOWN_LEFT_RIGHT_LEFT_RIGHT_BA"
        ]

        for code in new_cheat_codes:
            print(f"Sending cheat code: {code}")
            response = gen.send(code)

# Run the CheatCodeGenerator
if __name__ == "__main__":
    ccg = CheatCodeGenerator()
    ccg.run()