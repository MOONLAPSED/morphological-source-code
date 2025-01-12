class StatefulGenerator:
    def __init__(self):
        # Define authorized codes mapped to access levels or responses
        self.access_codes = {
            "AUTH_001": "Access Level 1 Granted",
            "AUTH_002": "Access Level 2 Granted",
            "AUTH_SUPER": "Superuser Access Granted"
        }
        self.state = "initializing"  # Initial generator state
        self.current_actor = None    # Tracks the current active user

    def authorize(self, code):
        """Authenticate access code and return corresponding access level."""
        return self.access_codes.get(code)

    def generator(self, initial_actor):
        """A stateful generator with controlled access and actor switching."""
        self.current_actor = initial_actor
        while True:
            # Initial state set-up or reset upon re-entry
            if self.state == "initializing":
                self.state = "awaiting authorization"
                print(f"{self.current_actor} - Ready. Awaiting authorization code.")
            
            # Yield the current state and wait for external input
            input_data = yield self.state
            
            # Handle actor-switching requests if input_data is structured as a dict
            if isinstance(input_data, dict) and "switch_actor" in input_data:
                new_actor = input_data["switch_actor"]
                auth_code = input_data.get("auth_code", "")
                print(f"Attempting to switch control to {new_actor}...")
                
                if self.authorize(auth_code):
                    # Switch control to the new actor if authorized
                    self.current_actor = new_actor
                    self.state = f"authorization success - control transferred to {new_actor}"
                    print(f"Control switched to {new_actor} with code: {auth_code}")
                else:
                    print("Authorization failed for control switch. Current actor remains.")
                continue  # Skip to the next yield
            
            # Process authorization attempts from the current actor
            if isinstance(input_data, str):
                auth_response = self.authorize(input_data)
                if auth_response:
                    # Update state based on successful authorization
                    self.state = auth_response
                    print(f"{self.current_actor}: Authorization succeeded - {auth_response}")
                else:
                    # Invalid code response
                    self.state = "Invalid authorization. Try again."
                    print(f"{self.current_actor}: {self.state}")

    def run(self):
        """Run the generator with an initial actor and test inputs."""
        initial_actor = "Actor1"
        gen = self.generator(initial_actor)
        next(gen)  # Initialize the generator coroutine

        # Testing authorization attempts from Actor1
        auth_codes_to_test = [
            "AUTH_001",
            "INVALID_CODE",
            "AUTH_SUPER"
        ]

        print("\n--- Actor1 Authorization Attempts ---")
        for code in auth_codes_to_test:
            print(f"{initial_actor} provides code: {code}")
            response = gen.send(code)  # Send authorization code to generator

        # Attempting to switch control to Actor2
        print("\n--- Attempting Control Transfer to Actor2 ---")
        new_actor_data = {
            "switch_actor": "Actor2",
            "auth_code": "AUTH_SUPER"  # Actor2 tries to assume control
        }
        response = gen.send(new_actor_data)  # Attempt control switch
        print(f"Generator state after switch: {response}")

        # Further testing with Actor2
        new_auth_codes = [
            "AUTH_002",
            "AUTH_001"
        ]

        print("\n--- Actor2 Authorization Attempts ---")
        for code in new_auth_codes:
            print(f"Actor2 provides code: {code}")
            response = gen.send(code)

# Execute StatefulGenerator
if __name__ == "__main__":
    sg = StatefulGenerator()
    sg.run()
