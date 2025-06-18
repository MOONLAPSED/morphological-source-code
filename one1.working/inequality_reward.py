import random
from collections import defaultdict
from typing import Tuple, List, Dict

# Parameters
ALPHA = 0.1  # Learning rate
GAMMA = 0.9  # Discount factor
EPSILON = 0.1  # Exploration rate
EPISODES = 50

# Bell's inequality constants
MEASUREMENT_SETTINGS = [(0, 0), (0, 1), (1, 0), (1, 1)]  # (setting for Alice, setting for Bob)
POSSIBLE_OUTCOMES = [-1, 1]  # Spin up or down

# Environment
def simulate_measurement(setting_A: int, setting_B: int, hidden_variable: float) -> Tuple[int, int]:
    """Simulate a measurement outcome for Alice and Bob based on settings and hidden variables."""
    # Simplified quantum correlation model
    outcome_A = 1 if random.random() < 0.5 + 0.5 * hidden_variable * setting_A else -1
    outcome_B = 1 if random.random() < 0.5 + 0.5 * hidden_variable * setting_B else -1
    return outcome_A, outcome_B

# Reward function
def reward_function(outcomes: List[Tuple[int, int]]) -> int:
    """Calculate reward based on Bell's inequality."""
    count = 0
    for (a, b), (a_prime, b_prime) in zip(outcomes[:-1], outcomes[1:]):
        count += (a == b) and (a_prime != b_prime)
    return 100 if count > 0 else -1

# Agent
class BellAgent:
    def __init__(self):
        self.q_table = defaultdict(lambda: defaultdict(float))

    def choose_action(self, state: Tuple, actions: List[Tuple[int, int]]) -> Tuple[int, int]:
        if random.random() < EPSILON:  # Explore
            return random.choice(actions)
        else:  # Exploit
            return max(actions, key=lambda a: self.q_table[state][a], default=random.choice(actions))

    def update_q_value(self, state, action, reward, next_state, next_actions):
        max_q_next = max([self.q_table[next_state][a] for a in next_actions], default=0)
        self.q_table[state][action] += ALPHA * (reward + GAMMA * max_q_next - self.q_table[state][action])

# Run Simulation
def run_simulation():
    agent = BellAgent()
    actions = MEASUREMENT_SETTINGS
    for episode in range(EPISODES):
        state = random.random()  # Hidden variable for this run
        outcomes = []
        while len(outcomes) < 10:  # Collect 10 measurements
            action = agent.choose_action((state,), actions)
            outcome_A, outcome_B = simulate_measurement(action[0], action[1], state)
            outcomes.append((outcome_A, outcome_B))
            reward = reward_function(outcomes)
            next_state = state  # Hidden variable doesn't change
            agent.update_q_value((state,), action, reward, (next_state,), actions)
    return agent.q_table

# Train the agent
q_table = run_simulation()

# Display results
print("Trained Q-Table:")
for state, actions in q_table.items():
    print(f"State: {state}, Actions: {actions}")
