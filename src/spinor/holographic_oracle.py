# holographic_oracle.py (ctypes wrapper)
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
import subprocess
import ctypes
import platform
import json


# Load the Racket **shared library** (not executable!)
def load_racket_boundary():
    """Load libracket_spinor.so/dll as a C extension"""
    if platform.system() == "Windows":
        lib = ctypes.CDLL("./racket/libracket_spinor.dll")
    else:
        lib = ctypes.CDLL("./racket/libracket_spinor.so")

    # Racket exports **topological primitives**
    lib.measure_topological_coherence.argtypes = [ctypes.c_int]
    lib.measure_topological_coherence.restype = ctypes.c_double  # probability

    lib.get_holographic_operator.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.get_holographic_operator.restype = ctypes.c_void_p  # opaque handle

    lib.apply_operator.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    lib.apply_operator.restype = ctypes.c_int

    return lib


_boundary_oracle = load_racket_boundary()


def get_topological_coherence(spinor_value: int) -> float:
    """
    Python phenomenology → Racket boundary → C bulk
    Returns: probability that spinor is "well-formed" in the ontology
    """
    return _boundary_oracle.measure_topological_coherence(spinor_value)


def get_holographic_operator(op_name: str, arity: int) -> int:
    """
    Get a **compiled operator** from Racket that Python can call into C
    """
    return _boundary_oracle.get_holographic_operator(op_name.encode(), arity)


def apply_operator(handle: int, a: int, b: int) -> int:
    """Apply Racket-scripted operator in C bulk"""
    return _boundary_oracle.apply_operator(handle, a, b)


class RacketOracle:
    def __init__(self, racket_exe: str = None):
        self.exe = racket_exe or self._find_racket()

    def _find_racket(self):
        import platform

        base = Path(__file__).parent / "racket"
        if platform.system() == "Windows":
            return str(base / "holographic_spinor.exe")
        return str(base / "holographic-spinor")

    def query(self, command: str, **params) -> dict:
        """Generic query to Racket boundary oracle"""
        args = [self.exe, f"--{command}", json.dumps(params)]
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return json.loads(result.stdout.strip())


# Usage in MSC_core.py
_oracle = RacketOracle()


class ByteWord:
    def measure_topology(self) -> dict:
        """Ask Racket: 'Is this spinor coherent?'"""
        return _oracle.query("measure", value=self.raw)

    def get_operator(self, op_name: str):
        """Ask Racket: 'Give me the compiled operator for this'"""
        return _oracle.query("operator", name=op_name, input=self.raw)


# Compile Racket-generated C code on the fly
c_code = get_holographic_operator("xor", 2)
with open("_temp_operator.c", "w") as f:
    f.write(c_code)

subprocess.run(["gcc", "-fPIC", "-shared", "_temp_operator.c", "-o", "_operator.so"])

# Load the compiled operator
operator_lib = ctypes.CDLL("./_operator.so")
operator_lib.measure_topology.argtypes = [ctypes.c_int]
operator_lib.measure_topology.restype = ctypes.c_int

# Call it directly in C!
result = operator_lib.measure_topology(240)  # No Racket overhead
