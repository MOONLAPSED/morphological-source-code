import hashlib

# Mapping hexadecimal digits to colors
COLOR_MAP = {
    '0': '31',  # Red
    '1': '32',  # Green
    '2': '33',  # Yellow
    '3': '34',  # Blue
    '4': '35',  # Magenta
    '5': '36',  # Cyan
    '6': '37',  # White
    '7': '38',  # Grey
    '8': '39',  # Dark Red
    '9': '40',  # Dark Green
    'a': '41',  # Dark Yellow
    'b': '42',  # Dark Blue
    'c': '43',  # Dark Magenta
    'd': '44',  # Dark Cyan
    'e': '45',  # Light Red
    'f': '46',  # Light Green
}

def colorize_hash(hash_string):
    """
    Takes a SHA256 hash string and returns it with colorized nibbles.
    Each nibble (hex digit) is assigned a unique color.
    """
    colored_hash = ""
    for char in hash_string:
        color_code = COLOR_MAP.get(char.lower(), '37')  # Default to white if not found
        colored_hash += f"\033[38;5;{color_code}m{char}\033[0m"  # ANSI escape code for color
    return colored_hash

def generate_merkle_root(data):
    """
    Generate a Merkle root hash for the given data (list of strings).
    """
    hashes = [hashlib.sha256(d.encode()).hexdigest() for d in data]

    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])  # If odd, duplicate last hash
        hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest() for i in range(0, len(hashes), 2)]

    return hashes[0]

def main():
    # Sample data (replace with your actual frames/data)
    frames = ['lambda', 'x)', 'y)', 'z)']
    
    # Generate the Merkle root
    merkle_root = generate_merkle_root(frames)
    
    # Print the surface form with colorized hash nibbles
    for frame in frames:
        # Print the original text and its corresponding colorized hash
        hash_value = hashlib.sha256(frame.encode()).hexdigest()
        print(f"Surface form: {frame}")
        print(f"Colorized hash: {colorize_hash(hash_value)}")

    print(f"Generated Merkle Root (Colorized): {colorize_hash(merkle_root)}")

if __name__ == '__main__':
    main()
