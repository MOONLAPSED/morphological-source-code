import cmath
import math

# Define your density matrices for each step as lists of lists with complex numbers
"""
density_matrices = [
    [[1.000, 0.000], [0.000, 0.000]],  # Step 1
    [[0.990, 0.028 - 0.042j], [0.028 + 0.042j, 0.010]],  # Step 2
    [[0.975, 0.056 - 0.083j], [0.056 + 0.083j, 0.025]],  # Step 3
    [[0.955, 0.083 - 0.123j], [0.083 + 0.123j, 0.045]],  # Step 4
    [[0.930, 0.109 - 0.160j], [0.109 + 0.160j, 0.070]]   # Step 5
]
density_matrices = [
    # Step 1
    [[1.000, 0.000],
     [0.000, 0.000]],

    # Step 2
    [[0.990, 0.039 - 0.040j],
     [0.039 + 0.040j, 0.010]],

    # Step 3
    [[0.974, 0.079 - 0.077j],
     [0.079 + 0.077j, 0.026]],

    # Step 4
    [[0.952, 0.119 - 0.110j],
     [0.119 + 0.110j, 0.048]],

    # Step 5
    [[0.924, 0.160 - 0.139j],
     [0.160 + 0.139j, 0.076]]
]
"""
density_matrices = [
    # Step 1
    [[1.000, 0.000],
     [0.000, 0.000]],

    # Step 2
    [[0.990, 0.039 + 0.001j],
     [0.039 - 0.001j, 0.010]],

    # Step 3
    [[0.977, 0.078],
     [0.078, 0.023]],

    # Step 4
    [[0.961, 0.115 - 0.003j],
     [0.115 + 0.003j, 0.039]],

    # Step 5
    [[0.943, 0.150 - 0.009j],
     [0.150 + 0.009j, 0.057]]
]

def trace(matrix):
    """Calculate the trace of a 2x2 matrix."""
    return matrix[0][0] + matrix[1][1]

def matrix_multiply(m1, m2):
    """Multiply two 2x2 matrices."""
    return [
        [
            m1[0][0] * m2[0][0] + m1[0][1] * m2[1][0],
            m1[0][0] * m2[0][1] + m1[0][1] * m2[1][1]
        ],
        [
            m1[1][0] * m2[0][0] + m1[1][1] * m2[1][0],
            m1[1][0] * m2[0][1] + m1[1][1] * m2[1][1]
        ]
    ]

def purity(matrix):
    """Calculate the purity of a density matrix (Tr(rho^2))."""
    squared_matrix = matrix_multiply(matrix, matrix)
    return trace(squared_matrix).real

def eigenvalues(matrix):
    """Calculate eigenvalues for a 2x2 Hermitian matrix."""
    a, d = matrix[0][0], matrix[1][1]
    b, c = matrix[0][1], matrix[1][0]
    tr = a + d
    det = a * d - b * c
    # Quadratic formula for eigenvalues
    term = cmath.sqrt(tr**2 - 4 * det)
    lambda1 = (tr + term) / 2
    lambda2 = (tr - term) / 2
    return [lambda1.real, lambda2.real]

def entropy(eigenvalues):
    """Calculate von Neumann entropy from eigenvalues."""
    entropy_value = -sum(l * math.log(l + 1e-10) for l in eigenvalues if l > 0)
    return entropy_value

def coherence(matrix):
    """Calculate the magnitude of the off-diagonal term (coherence)."""
    return abs(matrix[0][1])

# Iterate over each density matrix and calculate metrics
for i, rho in enumerate(density_matrices):
    purity_value = purity(rho)
    entropy_value = entropy(eigenvalues(rho))
    coherence_value = coherence(rho)

    print(f"Step {i + 1}:")
    print(f"  Purity: {purity_value:.6f}")
    print(f"  Entropy: {entropy_value:.6f}")
    print(f"  Coherence (|rho_01|): {coherence_value:.6f}\n")
