import asyncio
import hashlib

class Lexer:
    def __init__(self):
        self.frames = []

    def color_text(self, text, color_code):
        """
        Apply color to the text using ANSI escape sequences.
        """
        return f"\033[38;5;{color_code}m{text}\033[0m"

    def generate_merkle_root(self, frames):
        """
        Generates a Merkle root hash from the provided frames.
        """
        hashes = frames  # Assuming 'frames' is a list of data

        # Processing hashes in pairs
        while len(hashes) > 1:
            # If there's an odd number of hashes, append the last one as is
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])  # Optionally apply fallback logic here
            
            # Hash the pairs
            hashes = [self._hash_pair(hashes[i], hashes[i+1]) for i in range(0, len(hashes) - 1, 2)]

        return hashes[0] if hashes else None

    def _hash_pair(self, hash1, hash2):
        """
        Combine and hash two elements to form a new hash.
        """
        combined = hash1 + hash2
        return hashlib.sha256(combined.encode()).hexdigest()

async def main():
    lexer = Lexer()

    # Sample frames (you can replace this with your actual data)
    frames = ['lambda', 'x)', 'y)', 'z)']

    # Generate the Merkle root
    root = lexer.generate_merkle_root(frames)

    # Print the results with color
    for frame in frames:
        color_tag = "edf8e3"  # Example color, replace with your logic
        print(f"Surface form: {lexer.color_text(frame, color_tag)}")

    print(f"Generated Merkle Root: {root}")

# Run the asyncio main function
if __name__ == '__main__':
    asyncio.run(main())
