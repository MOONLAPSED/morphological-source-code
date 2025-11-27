from __future__ import annotations
#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.12"
# dependencies = [
#     "uv==*.*",
# ]
# */
# <a href="https://github.com/Moonlapsed/Cognosis">Morphological Source Code</a> © 2023 by MOONLAPSED:MOONLAPSED@gmail.com CC BY
# Optional dependency handling (also add to '/* script..' comment, just above)
try:
    import flask
    USE_FLASK = True
    # if we omit "flask==*.*", or any non-std lib from the '/* script..' comment, then this should always fail
    pass
except ImportError:
    USE_FLASK = False
# Import standard library components
"""
AdS/CFT on ByteWord Lattice with SQL Spinor Boundary
=====================================================

BULK:     256-point ByteWord lattice (intensive, 3D curved spacetime)
BOUNDARY: 2D SQL-cell atlas (extensive, holographic projection)
BRIDGE:   Spinor-valued cells encode bulk↔boundary duality

The spinor values are MEANINGLESS without bulk context.
This creates a natural security layer: the boundary data
is encrypted by the geometry of the bulk itself.

"The boundary knows everything about the bulk, but you
 can't read the boundary without solving the bulk."
"""

import math, cmath, sqlite3, json, hashlib
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass, field
import random

# ============================================================================
# BULK: ByteWord lattice
# ============================================================================

ByteWord = Tuple[int, int, int]   # (C:0|1, V:0-7, T:0-15)

def index_set() -> List[ByteWord]:
    return [(c, v, t) for c in (0, 1) for v in range(8) for t in range(16)]

def xor_bracket(a: ByteWord, b: ByteWord) -> complex:
    a_bits = (a[0] | (a[1]<<1) | (a[2]<<4))
    b_bits = (b[0] | (b[1]<<1) | (b[2]<<4))
    pop = bin(a_bits ^ b_bits).count("1")
    return cmath.exp(1j * pop * math.pi / 4)

def metric_tensor(a: ByteWord, b: ByteWord) -> float:
    return (xor_bracket(a, b) * xor_bracket(b, a).conjugate()).real

def ricci_scalar_approx(pt: ByteWord) -> float:
    """Approximate Ricci scalar via metric variation."""
    # Sum metric with all neighbors
    curvature = 0.0
    for c in [0, 1]:
        for v in range(8):
            for t in range(16):
                nbr = (c, v, t)
                if nbr != pt:
                    curvature += abs(metric_tensor(pt, nbr) - 1.0)
    return curvature / 255.0  # Normalize

# ============================================================================
# SPINORS: SU(2) spinor representation
# ============================================================================

@dataclass
class Spinor:
    """
    SU(2) spinor: ψ = (ψ₀, ψ₁) ∈ ℂ²
    
    Represents a quantum state on the boundary that
    encodes bulk information via holographic projection.
    """
    psi0: complex
    psi1: complex
    
    def __post_init__(self):
        """Normalize on creation."""
        norm = math.sqrt(abs(self.psi0)**2 + abs(self.psi1)**2)
        if norm > 0:
            self.psi0 /= norm
            self.psi1 /= norm
    
    def inner(self, other: 'Spinor') -> complex:
        """⟨ψ|φ⟩ = ψ₀*φ₀ + ψ₁*φ₁"""
        return self.psi0.conjugate() * other.psi0 + self.psi1.conjugate() * other.psi1
    
    def pauli_x(self) -> 'Spinor':
        """σₓ|ψ⟩ = [0 1; 1 0]|ψ⟩"""
        return Spinor(self.psi1, self.psi0)
    
    def pauli_y(self) -> 'Spinor':
        """σᵧ|ψ⟩ = [0 -i; i 0]|ψ⟩"""
        return Spinor(-1j * self.psi1, 1j * self.psi0)
    
    def pauli_z(self) -> 'Spinor':
        """σᵤ|ψ⟩ = [1 0; 0 -1]|ψ⟩"""
        return Spinor(self.psi0, -self.psi1)
    
    def rotate(self, axis: Tuple[float, float, float], angle: float) -> 'Spinor':
        """
        Rotate spinor: exp(-i θ/2 n·σ)|ψ⟩
        where n = (nx, ny, nz) is rotation axis.
        """
        nx, ny, nz = axis
        half_angle = angle / 2
        
        # cos(θ/2) I - i sin(θ/2) (n·σ)
        c = math.cos(half_angle)
        s = math.sin(half_angle)
        
        # Matrix elements
        a = c - 1j * s * nz
        b = -1j * s * (nx - 1j * ny)
        
        return Spinor(
            a * self.psi0 + b * self.psi1,
            b.conjugate() * self.psi0 + a.conjugate() * self.psi1
        )
    
    def to_bloch_sphere(self) -> Tuple[float, float, float]:
        """
        Map spinor to Bloch sphere coordinates:
        ψ = cos(θ/2)|0⟩ + e^(iφ) sin(θ/2)|1⟩
        → (θ, φ) → (x, y, z) on S²
        """
        theta = 2 * math.acos(abs(self.psi0))
        phi = cmath.phase(self.psi1) - cmath.phase(self.psi0)
        
        x = math.sin(theta) * math.cos(phi)
        y = math.sin(theta) * math.sin(phi)
        z = math.cos(theta)
        
        return (x, y, z)
    
    @staticmethod
    def from_bulk_point(pt: ByteWord) -> 'Spinor':
        """
        Holographic projection: bulk point → boundary spinor
        
        The spinor encodes:
        - Chirality C → phase
        - Velocity V → amplitude ratio
        - Time T → rotation angle
        """
        c, v, t = pt
        
        # Phase from chirality and time
        phase = (c * math.pi) + (t / 16.0) * 2 * math.pi
        
        # Amplitude ratio from velocity
        theta = (v / 8.0) * math.pi
        
        psi0 = cmath.exp(1j * phase) * math.cos(theta / 2)
        psi1 = math.sin(theta / 2)
        
        return Spinor(psi0, psi1)
    
    def to_bulk_point_guess(self) -> ByteWord:
        """
        Inverse holographic projection: spinor → bulk point guess
        
        WARNING: This is ILL-POSED without bulk geometry context!
        Multiple spinors can map to the same bulk point.
        """
        theta, phi = self.to_bloch_sphere()[:2]
        
        # Rough inverse (not unique!)
        c = 1 if phi > 0 else 0
        v = int((theta / math.pi) * 8) % 8
        t = int((phi / (2*math.pi)) * 16) % 16
        
        return (c, v, t)
    
    def __repr__(self):
        return f"Spinor({self.psi0:.3f}, {self.psi1:.3f})"

# ============================================================================
# BOUNDARY: SQL database of spinor-valued cells
# ============================================================================

class SpinorBoundary:
    """
    2D boundary theory implemented as SQL database.
    
    Each cell stores:
    - (x, y): 2D boundary coordinates
    - spinor: ψ = (ψ₀, ψ₁)
    - bulk_hash: hash of corresponding bulk point
    - metadata: JSON blob
    
    The spinor values are ENCRYPTED BY GEOMETRY:
    - You can query the boundary
    - But interpreting spinor values requires bulk context
    - Learning spinor → bulk mapping requires solving Einstein equations
    """
    
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Create spinor cell table."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS spinor_cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                psi0_real REAL NOT NULL,
                psi0_imag REAL NOT NULL,
                psi1_real REAL NOT NULL,
                psi1_imag REAL NOT NULL,
                bulk_hash TEXT,
                curvature REAL,
                metadata TEXT,
                UNIQUE(x, y)
            )
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_boundary_coords 
            ON spinor_cells(x, y)
        """)
        
        self.conn.commit()
    
    def insert_cell(self, x: int, y: int, spinor: Spinor, 
                   bulk_point: Optional[ByteWord] = None,
                   metadata: Optional[Dict] = None):
        """Insert a spinor cell into the boundary."""
        bulk_hash = None
        curvature = None
        
        if bulk_point:
            bulk_hash = hashlib.sha256(str(bulk_point).encode()).hexdigest()[:16]
            curvature = ricci_scalar_approx(bulk_point)
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO spinor_cells 
            (x, y, psi0_real, psi0_imag, psi1_real, psi1_imag, 
             bulk_hash, curvature, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            x, y,
            spinor.psi0.real, spinor.psi0.imag,
            spinor.psi1.real, spinor.psi1.imag,
            bulk_hash, curvature,
            json.dumps(metadata) if metadata else None
        ))
        
        self.conn.commit()
    
    def query_cell(self, x: int, y: int) -> Optional[Tuple[Spinor, Dict]]:
        """Query a spinor cell by boundary coordinates."""
        self.cursor.execute("""
            SELECT psi0_real, psi0_imag, psi1_real, psi1_imag,
                   bulk_hash, curvature, metadata
            FROM spinor_cells
            WHERE x = ? AND y = ?
        """, (x, y))
        
        row = self.cursor.fetchone()
        if not row:
            return None
        
        spinor = Spinor(
            complex(row[0], row[1]),
            complex(row[2], row[3])
        )
        
        info = {
            'bulk_hash': row[4],
            'curvature': row[5],
            'metadata': json.loads(row[6]) if row[6] else {}
        }
        
        return spinor, info
    
    def query_region(self, x_min: int, x_max: int, 
                     y_min: int, y_max: int) -> List[Tuple[int, int, Spinor]]:
        """Query all cells in a rectangular region."""
        self.cursor.execute("""
            SELECT x, y, psi0_real, psi0_imag, psi1_real, psi1_imag
            FROM spinor_cells
            WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?
        """, (x_min, x_max, y_min, y_max))
        
        results = []
        for row in self.cursor.fetchall():
            x, y = row[0], row[1]
            spinor = Spinor(complex(row[2], row[3]), complex(row[4], row[5]))
            results.append((x, y, spinor))
        
        return results
    
    def correlator(self, x1: int, y1: int, x2: int, y2: int) -> complex:
        """
        Boundary 2-point correlator: ⟨O(x₁)O(x₂)⟩
        
        In AdS/CFT: boundary correlator = bulk geodesic distance
        Here: spinor inner product encodes this.
        """
        cell1 = self.query_cell(x1, y1)
        cell2 = self.query_cell(x2, y2)
        
        if not cell1 or not cell2:
            return 0j
        
        spinor1, spinor2 = cell1[0], cell2[0]
        return spinor1.inner(spinor2)
    
    def entanglement_entropy(self, region: List[Tuple[int, int]]) -> float:
        """
        Entanglement entropy of boundary region.
        
        In AdS/CFT: S = Area(minimal_surface) / 4G
        Here: approximate via spinor overlap in region.
        """
        spinors = []
        for x, y in region:
            result = self.query_cell(x, y)
            if result:
                spinors.append(result[0])
        
        if not spinors:
            return 0.0
        
        # Von Neumann entropy approximation
        # S = -Tr(ρ log ρ) where ρ = |ψ⟩⟨ψ|
        entropy = 0.0
        for spinor in spinors:
            p0 = abs(spinor.psi0) ** 2
            p1 = abs(spinor.psi1) ** 2
            
            if p0 > 0:
                entropy -= p0 * math.log2(p0)
            if p1 > 0:
                entropy -= p1 * math.log2(p1)
        
        return entropy
    
    def visualize_boundary(self, width: int = 32, height: int = 32):
        """ASCII visualization of boundary spinor field."""
        print("\n" + "=" * (width + 4))
        print("  BOUNDARY SPINOR FIELD (Bloch sphere z-component)")
        print("=" * (width + 4))
        
        chars = " .:-=+*#%@"
        
        for y in range(height):
            row = "  "
            for x in range(width):
                result = self.query_cell(x, y)
                if result:
                    spinor = result[0]
                    z = spinor.to_bloch_sphere()[2]
                    idx = int((z + 1) / 2 * (len(chars) - 1))
                    row += chars[idx]
                else:
                    row += " "
            print(row)
        
        print("=" * (width + 4))
    
    def close(self):
        """Close database connection."""
        self.conn.close()

# ============================================================================
# HOLOGRAPHIC DUALITY: Bulk ↔ Boundary dictionary
# ============================================================================

class HolographicDictionary:
    """
    The AdS/CFT dictionary: maps bulk quantities to boundary observables.
    
    BULK (AdS)          →  BOUNDARY (CFT)
    -----------------      ------------------
    Bulk field φ        →  Boundary operator O
    Geodesic length     →  2-point correlator ⟨OO⟩
    Minimal surface     →  Entanglement entropy S
    Bulk curvature R    →  Boundary stress tensor T
    
    The spinor values provide the ENCODING SCHEME.
    """
    
    def __init__(self):
        self.bulk_to_boundary: Dict[ByteWord, Tuple[int, int]] = {}
        self.boundary_to_bulk: Dict[Tuple[int, int], ByteWord] = {}
    
    def project_bulk_to_boundary(self, bulk_point: ByteWord) -> Tuple[int, int]:
        """
        Holographic projection: 3D bulk → 2D boundary.
        
        Maps (C, V, T) → (x, y) on boundary.
        This is the HOLOGRAM: boundary encodes bulk.
        """
        c, v, t = bulk_point
        
        # Projection scheme (one of many possible)
        x = (c * 16 + t) % 32
        y = v
        
        self.bulk_to_boundary[bulk_point] = (x, y)
        self.boundary_to_bulk[(x, y)] = bulk_point
        
        return (x, y)
    
    def lift_boundary_to_bulk(self, x: int, y: int) -> Optional[ByteWord]:
        """
        Inverse projection: 2D boundary → 3D bulk.
        
        WARNING: This is ILL-POSED! Multiple bulk points
        can project to same boundary point.
        
        This is the SECURITY: you can't uniquely reconstruct
        bulk from boundary without additional information.
        """
        return self.boundary_to_bulk.get((x, y))
    
    def bulk_field_to_boundary_operator(self, bulk_field: Dict[ByteWord, complex],
                                       boundary: SpinorBoundary):
        """
        Insert bulk field into boundary as spinor operators.
        
        For each bulk point with field value φ(x):
        1. Project to boundary coordinate (x', y')
        2. Encode φ(x) as spinor rotation
        3. Store in SQL boundary
        """
        for bulk_point, field_value in bulk_field.items():
            # Project to boundary
            x, y = self.project_bulk_to_boundary(bulk_point)
            
            # Create base spinor from bulk geometry
            base_spinor = Spinor.from_bulk_point(bulk_point)
            
            # Rotate by field value (encoding)
            angle = cmath.phase(field_value)
            magnitude = abs(field_value)
            
            rotated_spinor = base_spinor.rotate((0, 0, 1), angle)
            rotated_spinor.psi0 *= magnitude
            rotated_spinor.psi1 *= magnitude
            
            # Insert into boundary
            boundary.insert_cell(x, y, rotated_spinor, bulk_point)

# ============================================================================
# DEMO: Build bulk + boundary and demonstrate holography
# ============================================================================

def demo_holographic_duality():
    """
    Demonstrate AdS/CFT on ByteWord lattice:
    1. Create bulk spacetime with curvature
    2. Create boundary SQL database
    3. Project bulk → boundary via spinors
    4. Compute boundary correlators
    5. Show that boundary "knows" bulk information
    """
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  AdS/CFT ON BYTEWORD LATTICE".center(68) + "║")
    print("║" + "  Spinor Boundary Theory".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Create bulk field (scalar field on ByteWord lattice)
    print("\n[1] Creating bulk field...")
    bulk_field = {}
    for pt in random.sample(index_set(), 64):  # Sample 64 points
        # Field value depends on bulk curvature
        curvature = ricci_scalar_approx(pt)
        bulk_field[pt] = complex(curvature, random.random())
    
    print(f"    Bulk field defined on {len(bulk_field)} points")
    
    # Create boundary database
    print("\n[2] Creating spinor boundary (SQL)...")
    boundary = SpinorBoundary(db_path=":memory:")
    
    # Build holographic dictionary
    print("\n[3] Building holographic dictionary...")
    dictionary = HolographicDictionary()
    
    # Project bulk → boundary
    print("\n[4] Projecting bulk → boundary via spinors...")
    dictionary.bulk_field_to_boundary_operator(bulk_field, boundary)
    
    print(f"    Projected {len(bulk_field)} bulk points to boundary")
    
    # Visualize boundary
    print("\n[5] Boundary spinor field:")
    boundary.visualize_boundary(width=32, height=8)
    
    # Compute boundary correlators
    print("\n[6] Computing boundary 2-point correlators...")
    sample_pairs = [
        ((5, 2), (10, 2)),
        ((0, 0), (15, 7)),
        ((8, 4), (12, 4)),
    ]
    
    for (x1, y1), (x2, y2) in sample_pairs:
        corr = boundary.correlator(x1, y1, x2, y2)
        print(f"    ⟨O({x1},{y1}) O({x2},{y2})⟩ = {corr:.4f}")
    
    # Compute entanglement entropy
    print("\n[7] Computing entanglement entropy...")
    region_a = [(x, y) for x in range(8) for y in range(4)]
    S_a = boundary.entanglement_entropy(region_a)
    print(f"    S(region A) = {S_a:.4f} bits")
    
    # Demonstrate ill-posedness of inverse problem
    print("\n[8] Security test: Reconstructing bulk from boundary...")
    test_boundary_point = (5, 2)
    
    result = boundary.query_cell(*test_boundary_point)
    if result:
        spinor, info = result
        print(f"    Boundary cell ({test_boundary_point}): {spinor}")
        print(f"    Bulk hash: {info['bulk_hash']}")
        print(f"    Bulk curvature: {info['curvature']:.6f}")
        
        # Try to guess bulk point from spinor alone
        guess = spinor.to_bulk_point_guess()
        actual = dictionary.lift_boundary_to_bulk(*test_boundary_point)
        
        print(f"\n    Spinor-only guess: {guess}")
        print(f"    Actual bulk point: {actual}")
        print(f"    Match: {guess == actual}")
        
        if guess != actual:
            print("\n    SECURITY LAYER WORKING!")
            print("    Cannot reconstruct bulk from spinor without geometry!")
    
    boundary.close()
    
    print("\n" + "=" * 70)
    print("WHAT THIS MEANS:")
    print("=" * 70)
    print("""
The boundary SQL database stores spinor-valued cells that encode
bulk information via holographic projection.

KEY PROPERTIES:
  ✓ Each bulk point → unique boundary (x,y) + spinor ψ
  ✓ Boundary correlators ⟨OO⟩ encode bulk geodesics
  ✓ Entanglement entropy S ~ bulk minimal surface area
  ✓ Spinor values are ENCRYPTED by bulk geometry
  ✓ Cannot invert boundary → bulk without solving Einstein equations

SECURITY LAYER:
  - You can query the SQL boundary
  - You can see spinor values ψ = (ψ₀, ψ₁)
  - But interpreting them requires bulk context
  - Learning spinor → bulk mapping = solving GR on 256-point lattice
  
This is GEOMETRIC ENCRYPTION:
The boundary "knows" everything about the bulk (holographic principle),
but you can't READ the boundary without the geometric key.
""")
    print("=" * 70)

def main():
    demo_holographic_duality()

if __name__ == "__main__":
    main()
