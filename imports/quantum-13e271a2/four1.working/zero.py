from typing import Dict, List, Optional
class ZeroCell:
    """
    Represents our minimal 7-bit unit, where:
    - T: 4 bits (type, address tag)
    - V: 2 bits (value or pointer)
    - C: 1 bit (control: 1=active, 0=dormant)
    """
    def __init__(self, value: int):
        if not 0 <= value <= 0x7F:
            raise ValueError("Value must be a 7-bit integer (0-127)")
        self.value = value  # 7 bits total

    @property
    def T(self) -> int:
        return (self.value >> 3) & 0x0F  # Top 4 bits

    @property
    def V(self) -> int:
        return (self.value >> 1) & 0x03  # Next 2 bits

    @property
    def C(self) -> int:
        return self.value & 0x01         # LSB

    def __repr__(self):
        return f"ZeroCell(0b{self.value:07b} | T={self.T}, V={self.V}, C={self.C})"

# Let's assume we have a global memory table for live cells:
global_memory: Dict[int, ZeroCell] = {}

def create_dormant_pointer(tag: int, pointer: int) -> ZeroCell:
    """
    Create a dormant (C=0) ZeroCell that encodes a pointer in its T and V fields.
    - 'tag' is stored in T (4 bits)
    - 'pointer' is stored in V (2 bits)
    """
    # Assemble the 7-bit value: T (4 bits), V (2 bits), and C=0.
    value = (tag & 0x0F) << 3 | (pointer & 0x03) << 1 | 0
    return ZeroCell(value)

def create_live_cell(tag: int, pointer: int) -> ZeroCell:
    """
    Create an active (C=1) ZeroCell.
    """
    value = (tag & 0x0F) << 3 | (pointer & 0x03) << 1 | 1
    return ZeroCell(value)

# Example:
dormant = create_dormant_pointer(tag=5, pointer=2)
live = create_live_cell(tag=7, pointer=1)

# Store live cell in our global memory table under index 2 (from pointer in dormant)
global_memory[2] = live

print("Dormant cell:", dormant)
print("Live cell:", live)

# Let's define a function to resolve a pointer:
def resolve(cell: ZeroCell) -> Optional[ZeroCell]:
    if cell.C == 0:  # Dormant: it acts as a pointer.
        pointer = cell.V
        return global_memory.get(pointer)
    else:
        return cell  # Already live.

resolved = resolve(dormant)
print("Resolved from dormant cell:", resolved)

# Additionally, a live cell can be composed from dormant ones:
def compose_live_from_dormant(cells: List[ZeroCell]) -> ZeroCell:
    """
    Combine several dormant cells to produce a live cell.
    For simplicity, we sum their tags and pointers (modular arithmetic).
    """
    total_tag = sum(cell.T for cell in cells) % 16
    total_pointer = sum(cell.V for cell in cells) % 4
    return create_live_cell(total_tag, total_pointer)

composite_live = compose_live_from_dormant([dormant, dormant])
print("Composite live cell:", composite_live)
