from dataclasses import dataclass

@dataclass
class GeneratorResponse:
    status: str
    message: str
    code: int = 0  # Default code, optional

def controlled_generator():
    # Initial setup
    response = GeneratorResponse(status="waiting", message="Please provide input.")
    data = yield response  # First yield with initial response
    
    while True:
        if data == "Next":
            response = GeneratorResponse(status="proceeding", message="Next stage reached.")
            data = yield response
        elif data == "Reset":
            response = GeneratorResponse(status="reset", message="Returning to initial state.")
            data = yield response
        else:
            response = GeneratorResponse(status="error", message="Invalid input. Try again.")
            data = yield response

# Create the generator
gen = controlled_generator()

# Start the generator and get the first response
response = next(gen)
print(response)  # GeneratorResponse(status='waiting', message='Please provide input.', code=0)

# Send 'Next' to progress the generator
response = gen.send("Next")
print(response)  # GeneratorResponse(status='proceeding', message='Next stage reached.', code=0)

# Send 'Reset' to reset the generator
response = gen.send("Reset")
print(response)  # GeneratorResponse(status='reset', message='Returning to initial state.', code=0)

# Send an invalid command
response = gen.send("Invalid Command")
print(response)  # GeneratorResponse(status='error', message='Invalid input. Try again.', code=0)
