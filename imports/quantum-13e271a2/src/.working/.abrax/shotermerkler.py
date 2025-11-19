import asyncio

class Lexer:
    def __init__(self):
        pass

    def _hash_pair(self, a, b):
        # Example hash pair function, replace with your actual logic
        return f"hashed_{a}_{b}"

    def generate_merkle_root(self, frames):
        # Your frames processing logic here, assuming it generates 'hashes' list
        hashes = self._generate_hashes(frames)

        # Process the hashes in pairs
        hashes = [self._hash_pair(hashes[i], hashes[i+1]) for i in range(0, len(hashes) - 1, 2)]

        # If there's an odd number of hashes, the last one doesn't have a pair.
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])  # You can choose to do something else for the last item

        return hashes

    def _generate_hashes(self, frames):
        # Dummy implementation, replace with your actual logic to generate hashes
        return [str(frame) for frame in frames]

def color_text(text, color_code):
    """Apply color to the text for CLI output using ANSI escape codes."""
    return f"\033[38;5;{color_code}m{text}\033[0m"

async def main():
    lexer = Lexer()
    frames = ['lambda', 'x_class']  # Sample input, replace with your actual input
    root = lexer.generate_merkle_root(frames)

    # Example output with colored text
    for item in root:
        print(color_text(item, 34))  # Blue color for the output text (change color code as needed)

if __name__ == "__main__":
    asyncio.run(main())
