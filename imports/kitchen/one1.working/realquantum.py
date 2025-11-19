from math import sqrt
import cmath
from collections import namedtuple
from functools import reduce
from operator import mul

class DegreesOfFreedom:
    def __init__(self, dimensions):
        """Base class for degrees of freedom in Hilbert space."""
        self.dimensions = dimensions  # Number of DOFs (e.g., 3 for space, 1 for spin)
        self.state_vector = [complex(0, 0)] * (2 ** dimensions)  # Default state vector (complex amplitudes)
        
    def normalize(self):
        """Normalize the state vector."""
        norm = sqrt(sum(abs(x)**2 for x in self.state_vector))
        if norm != 0:
            self.state_vector = [x / norm for x in self.state_vector]
    
    def apply_operator(self, operator_matrix):
        """Apply a quantum operator to the state vector."""
        new_state = [
            sum(operator_matrix[i][j] * self.state_vector[j] for j in range(len(self.state_vector)))
            for i in range(len(self.state_vector))
        ]
        self.state_vector = new_state
        self.normalize()
    
    def get_state(self):
        """Return the current state vector."""
        return self.state_vector

class HilbertSpace:
    def __init__(self, n_qubits):
        self.dimension = 2 ** n_qubits  # 2^n dimensional for n qubits
        self.n_qubits = n_qubits
        
class QuantumState:
    def __init__(self, hilbert_space, initial_amplitudes=None):
        self.hilbert_space = hilbert_space
        if initial_amplitudes:
            if len(initial_amplitudes) != hilbert_space.dimension:
                raise ValueError("Initial amplitudes must match Hilbert space dimension")
            self.amplitudes = initial_amplitudes
        else:
            self.amplitudes = [complex(0, 0)] * hilbert_space.dimension
    
    def normalize(self):
        norm = sqrt(sum(abs(x)**2 for x in self.amplitudes))
        if norm != 0:
            self.amplitudes = [x / norm for x in self.amplitudes]

class QuantumOperator:
    def __init__(self, hilbert_space, matrix=None):
        self.hilbert_space = hilbert_space
        dim = hilbert_space.dimension
        if matrix:
            if len(matrix) != dim or any(len(row) != dim for row in matrix):
                raise ValueError("Operator matrix must match Hilbert space dimension")
            self.matrix = matrix
        else:
            self.matrix = [[complex(0, 0)] * dim for _ in range(dim)]
    
    def apply_to(self, state):
        if state.hilbert_space.dimension != self.hilbert_space.dimension:
            raise ValueError("Hilbert space dimensions don't match")
        result = [sum(self.matrix[i][j] * state.amplitudes[j] 
                 for j in range(self.hilbert_space.dimension))
                 for i in range(self.hilbert_space.dimension)]
        state.amplitudes = result
        state.normalize()

def main():
    hilbert_space = HilbertSpace(2)
    # Initialize state with |00⟩ + |11⟩ superposition
    initial_amplitudes = [1/sqrt(2), 0, 0, 1/sqrt(2)]
    state = QuantumState(hilbert_space, initial_amplitudes=initial_amplitudes)
    print(f'Initial State: {state.amplitudes}')
    
    # Define a simple operator (identity matrix for demonstration)
    operator_matrix = [[1, 0, 0, 0],
                       [0, 1, 0, 0],
                       [0, 0, 1, 0],
                       [0, 0, 0, 1]]
    operator = QuantumOperator(hilbert_space, matrix=operator_matrix)
    
    operator.apply_to(state)
    print(f'State after applying operator: {state.amplitudes}')

if __name__ == "__main__":
    main()