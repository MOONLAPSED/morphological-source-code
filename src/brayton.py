import math
"""The ideal Brayton cycle consists of:
    Isentropic Compression: From state 1 to 2 in the compressor.
    Isobaric Heat Addition: From state 2 to 3 in the combustion chamber.
    Isentropic Expansion: From state 3 to 4 in the turbine.
    Isobaric Heat Rejection: Returns the state from 4 to 1.
Assumptions:
    Air behaves as an ideal gas.
    Processes are either isentropic (constant entropy) or isobaric (constant pressure).
"""
# Constants
gamma = 1.4  # Heat capacity ratio for air
cp = 1004  # Specific heat at constant pressure (J/kg*K)

# Given temperatures (K)
T1 = 300  # Initial temperature
P1 = 101325  # Initial pressure (Pa)
P2 = 5 * P1  # Pressure after compression (example factor)

# Isentropic compression temperature ratio (T2/T1)
T2_T1_ratio = (P2 / P1) ** ((gamma - 1) / gamma)
T2 = T2_T1_ratio * T1

# Assume T3 after combustion and constant across states 2 to 3
T3 = 1600  # Post-combustion temperature (K)

# Isentropic expansion from T3 to T4 across Turbine
T4_T3_ratio = (P1 / P2) ** ((gamma - 1) / gamma)
T4 = T3 * T4_T3_ratio

# Efficiency of ideal cycle
efficiency = 1 - (T4 - T1) / (T3 - T2)

# Calculate net work (Substitute values and equations)
Wt = cp * (T3 - T4)  # Turbine work
Wc = cp * (T2 - T1)  # Compressor work
W_net = Wt - Wc

# Output results
print(f"T2/T1 Ratio: {T2_T1_ratio:.2f}")
print(f"T2 = {T2:.2f} K")
print(f"T4/T3 Ratio: {T4_T3_ratio:.2f}")
print(f"T4 = {T4:.2f} K")
print(f"Cycle Efficiency: {efficiency:.2f}")
print(f"Net Work per cycle: {W_net:.2f} J/kg")