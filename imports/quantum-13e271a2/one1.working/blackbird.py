# ---
# Constants
gamma = 1.4  # Heat capacity ratio for air
cp = 1004  # Specific heat at constant pressure (J/kg*K)
R = 287.05  # Specific gas constant for dry air (J/kg*K)

# Conceptual Model: "Blackbird_Box"
# - A theoretical propulsion system capable of sustaining Mach 2 at 60,000 feet 'for free'.
# - External forces, represented as being "towed" by a Wonder Woman's invisible jet, are out of
#   scope for this model, since we're focusing on the bootstrapping and maintenence of a cutting-
#   edge Brayton Cycle complex thermodynamic processes with no additional variables considered.
# - Combines dynamic subsystems: engine, turbine, scramjet effect, electrolysis, and methanation.

# Define Mach number for simulation
mach = 2.0  # Supersonic speed, twice the speed of sound

# Environmental Conditions at 60,000 feet and Mach 2
T1 = 216.65  # Static temperature in Kelvin
P1 = 19180   # Static pressure in Pascals
# real Blackbird is mach = 3, with different T1 and T2 values
# Calculate the total pressure ratio with air compression at Mach 2
pressure_ratio_static_to_total = (1 + ((gamma - 1) / 2) * mach**2) ** (gamma / (gamma - 1))
P2 = P1 * pressure_ratio_static_to_total  # Total pressure after compression

# Isentropic Compression and Expansion Calculations mimicking scramjet operation
T2_T1_ratio = (P2 / P1) ** ((gamma - 1) / gamma)
T2 = T1 * T2_T1_ratio  # Temperature after compression

# Assume a designed post-combustion temperature to explore output dynamics
# T3 computation coupled with chemical processes (e.g., electrolysis and methanation)

T3 = 1600  # Hypothetical high-temperature scenario induced by combustion

# Expansion computation based on idealized assumptions
T4_T3_ratio = (P1 / P2) ** ((gamma - 1) / gamma)
T4 = T3 * T4_T3_ratio

# Calculating Work Done by Turbine and Required Compressor Work
Wt = cp * (T3 - T4)  # Work output by turbine in J/kg
Wc = cp * (T2 - T1)  # Work input to compressor in J/kg

# Net work output and cycle efficiency
W_net = Wt - Wc
efficiency = 1 - (T4 - T1) / (T3 - T2)

# Output Results
print("------- Blackbird_box Brayton Cycle Analysis -------")
print(f"At Mach {mach} and 60,000 feet altitude:")
print(f"Static-to-Total Pressure Ratio: {pressure_ratio_static_to_total:.2f}")
print(f"Temperature after Compression (T2): {T2:.2f} K")
print(f"Temperature before Expansion (T3): {T3:.2f} K")
print(f"Temperature after Expansion (T4): {T4:.2f} K")
print(f"Ideal Brayton Cycle Efficiency: {efficiency * 100:.2f}%")
print(f"Net Work Output per Cycle: {W_net:.2f} J/kg")

# ---

# Constants specific for Blackbird comparison
Blackbird_mach = 3.2
Blackbird_T1 = 255.0  # Hypothetical static temperature for this scenario in Kelvin
Blackbird_P1 = 23900  # Hypothetical static pressure for the Blackbird altitude

# Calculate using Blackbird conditions
Blackbird_pressure_ratio_static_to_total = (1 + ((gamma - 1) / 2) * Blackbird_mach**2) ** (gamma / (gamma - 1))
Blackbird_P2 = Blackbird_P1 * Blackbird_pressure_ratio_static_to_total
Blackbird_T2_T1_ratio = (Blackbird_P2 / Blackbird_P1) ** ((gamma - 1) / gamma)
Blackbird_T2 = Blackbird_T1 * Blackbird_T2_T1_ratio

# Compare these values with those from the current Mach 2 scenario
print("--- Blackbird vs. Blackbird_box ---")
print(f"At Mach {Blackbird_mach} and 80,000 feet altitude:")
print(f"Blackbird Static-to-Total Pressure Ratio: {Blackbird_pressure_ratio_static_to_total:.2f}")
print(f"Temperature after Compression (Blackbird T2): {Blackbird_T2:.2f} K")
print(f"Current Mach: {mach}")
print(f"Current Static-to-Total Pressure Ratio: {pressure_ratio_static_to_total:.2f}")
print(f"Temperature after Compression (Current T2): {T2:.2f} K")