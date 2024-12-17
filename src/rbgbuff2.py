import math
import colorsys
from typing import List, Tuple

class SemanticColorMapper:
    """Maps semantic vectors to RGB color space"""
    @staticmethod
    def vector_to_rgb(
        vector: List[float], 
        normalization_method: str = 'minmax'
    ) -> Tuple[int, int, int]:
        """
        Convert a semantic vector to an RGB color representation
        
        Args:
            vector: Input semantic vector
            normalization_method: Method to normalize vector 
                                  ('minmax', 'zscore', 'sigmoid')
        
        Returns:
            RGB color tuple (0-255 range)
        """
        # Normalize the vector
        if normalization_method == 'minmax':
            # Min-Max scaling to [0, 1]
            min_val = min(vector)
            max_val = max(vector)
            normalized = [
                (x - min_val) / (max_val - min_val) if max_val != min_val else 0.5 
                for x in vector
            ]
        elif normalization_method == 'zscore':
            # Z-score normalization
            mean = sum(vector) / len(vector)
            std = math.sqrt(sum((x - mean) ** 2 for x in vector) / len(vector))
            normalized = [
                (x - mean) / std if std != 0 else 0.5 
                for x in vector
            ]
        elif normalization_method == 'sigmoid':
            # Sigmoid normalization
            normalized = [1 / (1 + math.exp(-x)) for x in vector]
        else:
            raise ValueError(f"Unknown normalization method: {normalization_method}")
        
        # Use first three components to map to RGB
        r = int(normalized[0] * 255) if len(normalized) > 0 else 128
        g = int(normalized[1] * 255) if len(normalized) > 1 else 128
        b = int(normalized[2] * 255) if len(normalized) > 2 else 128
        
        return (r, g, b)
    
    @staticmethod
    def rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space"""
        return colorsys.rgb_to_hsv(
            rgb[0] / 255.0, 
            rgb[1] / 255.0, 
            rgb[2] / 255.0
        )
    
    @staticmethod
    def hsv_to_semantic_vector(
        hsv: Tuple[float, float, float], 
        dimensions: int = 64
    ) -> List[float]:
        """
        Convert HSV back to a semantic vector
        
        This method demonstrates how color could represent semantic information
        """
        # Use HSV components to generate a semantic vector
        base_vector = [
            math.sin(hsv[0] * 2 * math.pi),  # Hue as cyclic component
            hsv[1],  # Saturation as intensity
            hsv[2],  # Value as magnitude
        ]
        
        # Expand to desired dimensions using periodic functions
        semantic_vector = []
        for i in range(dimensions):
            # Use different periodic functions to create varied representations
            if i % 3 == 0:
                semantic_vector.append(math.sin(base_vector[0] * (i + 1)))
            elif i % 3 == 1:
                semantic_vector.append(math.cos(base_vector[1] * (i + 1)))
            else:
                semantic_vector.append(math.tan(base_vector[2] * (i + 1)))
        
        return semantic_vector

def demonstrate_semantic_color_mapping():
    """Demonstrate semantic vector to RGB mapping"""
    # Create a sample semantic vector
    sample_vector = [0.1, 0.5, 0.9, 0.2, 0.7, 1.0]
    
    # Map to RGB
    rgb_color = SemanticColorMapper.vector_to_rgb(sample_vector)
    print("Semantic Vector:", sample_vector)
    print("Mapped RGB Color:", rgb_color)
    
    # Convert to HSV
    hsv_color = SemanticColorMapper.rgb_to_hsv(rgb_color)
    print("HSV Representation:", hsv_color)
    
    # Convert back to semantic vector
    reconstructed_vector = SemanticColorMapper.hsv_to_semantic_vector(hsv_color)
    print("Reconstructed Semantic Vector:", reconstructed_vector)

if __name__ == "__main__":
    demonstrate_semantic_color_mapping()