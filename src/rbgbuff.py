import math
import colorsys

def semantic_vector_to_rgb(vector: list[float]) -> tuple[int, int, int]:
    """
    Convert a semantic vector to an RGB color representation
    
    Transformation strategy:
    1. Normalize vector components to [0, 1] range
    2. Use first 3 components as RGB
    3. Preserve semantic relationships through color space
    """
    # Normalize vector components
    def normalize(x: float) -> float:
        # Sigmoid normalization to [0, 1]
        return 1 / (1 + math.exp(-x))
    
    # Take first 3 components, normalize them
    normalized = [normalize(x) for x in vector[:3]]
    
    # Ensure we have exactly 3 components
    while len(normalized) < 3:
        normalized.append(0.0)
    
    # Convert to RGB (0-255 range)
    rgb = [int(x * 255) for x in normalized]
    
    return tuple(rgb)

def rgb_to_semantic_vector(rgb: tuple[int, int, int], dimensions: int = 64) -> list[float]:
    """
    Reverse the mapping from RGB back to a semantic vector
    
    Inverse transformation:
    1. Normalize RGB to [0, 1]
    2. Apply inverse sigmoid
    3. Extend to required dimensions
    """
    # Normalize RGB to [0, 1]
    normalized = [x / 255.0 for x in rgb]
    
    # Inverse sigmoid
    def inverse_normalize(x: float) -> float:
        return -math.log((1 / x) - 1)
    
    # Convert back to semantic vector components
    semantic_components = [inverse_normalize(x) for x in normalized]
    
    # Extend to required dimensions
    while len(semantic_components) < dimensions:
        semantic_components.append(0.0)
    
    return semantic_components

class RGBSemanticMultiplexer:
    """
    Multiplexes semantic vectors into RGB color space
    Provides methods for encoding and decoding semantic information
    """
    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions
    
    def encode(self, semantic_vector: list[float]) -> tuple[int, int, int]:
        """Encode semantic vector as RGB"""
        return semantic_vector_to_rgb(semantic_vector)
    
    def decode(self, rgb: tuple[int, int, int]) -> list[float]:
        """Decode RGB back to semantic vector"""
        return rgb_to_semantic_vector(rgb, self.dimensions)
    
    def visualize_semantic_space(self, vectors: list[list[float]]) -> list[tuple[int, int, int]]:
        """
        Convert multiple semantic vectors to RGB representations
        Useful for visualizing high-dimensional semantic relationships
        """
        return [self.encode(vector) for vector in vectors]

def demonstrate_semantic_rgb_multiplexing():
    """Demonstrate the RGB semantic multiplexing concept"""
    # Create a multiplexer
    multiplexer = RGBSemanticMultiplexer(dimensions=64)
    
    # Example semantic vectors
    vectors = [
        [1.0, 2.0, 3.0, 0.5, -1.0] * 13,  # First vector
        [0.1, 0.2, 0.3, -0.5, 1.0] * 13,  # Second vector
        [-1.0, -2.0, -3.0, 0.5, 1.0] * 13  # Third vector
    ]
    
    # Convert to RGB
    rgb_representations = multiplexer.visualize_semantic_space(vectors)
    
    print("Semantic Vectors:")
    for i, (vector, rgb) in enumerate(zip(vectors, rgb_representations)):
        print(f"Vector {i+1}:")
        print(f"  Semantic: {vector[:5]}...")
        print(f"  RGB: {rgb}")
        
        # Demonstrate reversibility
        decoded_vector = multiplexer.decode(rgb)
        print(f"  Decoded: {decoded_vector[:5]}...")
        print()

if __name__ == "__main__":
    demonstrate_semantic_rgb_multiplexing()