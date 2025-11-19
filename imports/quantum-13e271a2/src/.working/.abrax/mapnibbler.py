import asyncio
import hashlib

class Lexer:
    def __init__(self):
        self.frames = []

    def color_nibble(self, nibble):
        """
        Return an ANSI colored text based on the nibble value.
        """
        color_code = {
            '0': '16', '1': '17', '2': '18', '3': '19', '4': '20', '5': '21', '6': '22', '7': '23',
            '8': '24', '9': '25', 'a': '26', 'b': '27', 'c': '28', 'd': '29', 'e': '30', 'f': '31'
        }
        return f"\033[38;5;{color_code[nibble]}m{nibble}\033[0m"

    def render_colored_hash(self, hash_str):
        """
        Render the hash string, colorizing each nibble.
        """
        colored_hash = ''.join([self.color_nibble(nibble) for nibble in hash_str])
        return colored_hash

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

    # Print the results with colorized hashes
    for frame in frames:
        hash_value = hashlib.sha256(frame.encode()).hexdigest()
        colored_hash = lexer.render_colored_hash(hash_value)
        print(f"Surface form: {frame}")
        print(f"Colored hash: {colored_hash}")

    print(f"Generated Merkle Root: {root}")

# Run the asyncio main function
if __name__ == '__main__':
    asyncio.run(main())
