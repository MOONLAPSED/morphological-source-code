from abc import ABC, abstractmethod
from typing import Any, Dict, Callable
from dataclasses import dataclass, field

@dataclass
class Condition:
    """Represents a state or condition in the system."""
    attributes: Dict[str, Any]

    def __repr__(self):
        return f"Condition({self.attributes})"

class Action(ABC):
    """Abstract base class for an elementary action or reaction."""
    @abstractmethod
    def execute(self, input_condition: Condition) -> Condition:
        """Transform an input condition into an output condition."""
        pass

@dataclass
class Reaction(Action):
    """Concrete implementation of an elementary reaction."""
    transformation: Callable[[Condition], Condition]

    def execute(self, input_condition: Condition) -> Condition:
        output_condition = self.transformation(input_condition)
        print(f"Reaction: {input_condition} -> {output_condition}")
        return output_condition

@dataclass
class Agency:
    """Represents an invariant agency catalyzing actions."""
    name: str
    rules: Dict[str, Action] = field(default_factory=dict)

    def perform_action(self, action_key: str, input_condition: Condition) -> Condition:
        if action_key not in self.rules:
            raise ValueError(f"Action {action_key} is not defined for agency {self.name}.")
        action = self.rules[action_key]
        print(f"Agency '{self.name}' performing action '{action_key}'...")
        return action.execute(input_condition)

    def add_action(self, action_key: str, action: Action):
        self.rules[action_key] = action
        print(f"Action '{action_key}' added to agency '{self.name}'.")

# Example: Define transformations
def collapse_wave_function(condition: Condition) -> Condition:
    """Simulates a quantum observation collapsing the wave function."""
    new_attributes = {**condition.attributes, "observed": True}
    return Condition(attributes=new_attributes)

def metabolize(condition: Condition) -> Condition:
    """Simulates metabolic transformation in an organism."""
    new_attributes = {**condition.attributes, "energy_level": condition.attributes.get("energy_level", 0) - 10}
    return Condition(attributes=new_attributes)

# Example usage
if __name__ == "__main__":
    # Define initial conditions
    initial_condition = Condition(attributes={"position": "indeterminate", "energy_level": 100})

    # Create reactions
    observation_reaction = Reaction(transformation=collapse_wave_function)
    metabolism_reaction = Reaction(transformation=metabolize)

    # Define an agency
    quantum_agency = Agency(name="QuantumObserver")
    quantum_agency.add_action("observe", observation_reaction)

    metabolic_agency = Agency(name="MetabolicProcess")
    metabolic_agency.add_action("metabolize", metabolism_reaction)

    # Perform actions
    observed_condition = quantum_agency.perform_action("observe", initial_condition)
    metabolized_condition = metabolic_agency.perform_action("metabolize", observed_condition)
