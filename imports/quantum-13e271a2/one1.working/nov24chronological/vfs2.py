import os
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
import struct
import importlib.util

# Constants
WORD_SIZE = 2  # 16-bit word (4 hex digits)
BASE_DIR = "/app/vmem"

@dataclass
class MemoryCell:
    """Represents a single addressable memory location."""
    value: bytes = b'\x00' * WORD_SIZE

class VirtualMemoryFS:
    def __init__(self):
        """Initialize the virtual memory filesystem structure."""
        self.base_path = Path(BASE_DIR)
        self.word_max = 0xFFFF  # Maximum address for 16-bit word
        self.memory_map: Dict[int, MemoryCell] = {}
        
        # Initialize directory structure
        self._init_directory_structure()
        
    def _init_directory_structure(self):
        """Create the directory structure based on word addressing."""
        for high_byte in range(0x100):
            dir_path = self.base_path / f"{high_byte:02x}"
            dir_path.mkdir(parents=True, exist_ok=True)
            self._ensure_init_py(dir_path)
            
    def _ensure_init_py(self, dir_path: Path):
        """Ensure __init__.py exists and properly initializes the segment."""
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_content = f"""
from dataclasses import dataclass
import array

@dataclass
class MemorySegment:
    data: array.array

segment = MemorySegment(array.array('B', [0] * 256))
"""
            init_file.write_text(init_content)
    
    def _address_to_path(self, address: int) -> Path:
        """Convert a 16-bit address to directory/file path."""
        if not 0 <= address <= self.word_max:
            raise ValueError(f"Address {address:04x} out of range")
            
        high_byte = (address >> 8) & 0xFF
        low_byte = address & 0xFF
        return self.base_path / f"{high_byte:02x}" / f"{low_byte:02x}.mem"

    def read(self, address: int) -> bytes:
        """Read a word from the specified address."""
        path = self._address_to_path(address)
        if address not in self.memory_map:
            try:
                with open(path, 'rb') as f:
                    data = f.read(WORD_SIZE) or b'\x00' * WORD_SIZE
                self.memory_map[address] = MemoryCell(data)
            except IOError:
                self.memory_map[address] = MemoryCell()
        return self.memory_map[address].value

    def write(self, address: int, value: bytes):
        """Write a word to the specified address."""
        if len(value) != WORD_SIZE:
            raise ValueError(f"Value must be {WORD_SIZE} bytes")
        path = self._address_to_path(address)
        
        # Update the memory map
        self.memory_map[address] = MemoryCell(value)
        
        # Write to file
        with open(path, 'wb') as f:
            f.write(value)
            
    def get_directory_segment(self, high_byte: int):
        """Get reference to runtime memory segment for a directory."""
        if not 0 <= high_byte <= 0xFF:
            raise ValueError("Invalid directory address")
            
        dir_path = self.base_path / f"{high_byte:02x}"
        if not dir_path.exists():
            raise ValueError("Directory does not exist")
            
        # Import the segment from the directory's __init__.py
        spec = importlib.util.spec_from_file_location(
            f"vmem_{high_byte:02x}",
            str(dir_path / "__init__.py")
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load segment {high_byte:02x}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.segment

# Example usage
def demo_usage():
    vmem = VirtualMemoryFS()
    
    # Write a 16-bit value
    addr = 0x1234
    value = struct.pack(">H", 0xABCD)
    vmem.write(addr, value)
    # writes to /c/ right now
    # Read it back
    read_value = vmem.read(addr)
    print(f"Read value from {addr:04x}: {struct.unpack('>H', read_value)[0]:04x}")
    
    # Get runtime segment
    segment = vmem.get_directory_segment(0x12)
    print(f"Segment 0x12 data: {segment.data[:10]}")

if __name__ == "__main__":
    demo_usage()