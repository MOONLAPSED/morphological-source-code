import inspect
import json
from pathlib import Path
from datetime import datetime
import hashlib

class CognitiveSystem:
    def __init__(self, name, **kwargs):
        self.name = name
        self.state = kwargs
        self.subsystems = {}
        self.source = inspect.getsource(self.__class__)
        self.history = []
        self._record_state()
    
    def add_subsystem(self, name, system):
        self.subsystems[name] = system
        self._record_state()
        return system
    
    def update_state(self, **kwargs):
        self.state.update(kwargs)
        self._record_state()
    
    def _record_state(self):
        state_hash = self._hash_state()
        timestamp = datetime.now().isoformat()
        self.history.append((timestamp, state_hash))
    
    def _hash_state(self):
        state_repr = json.dumps(self.state, sort_keys=True)
        return hashlib.sha256(state_repr.encode()).hexdigest()[:8]
    
    def save(self, base_dir=Path("cognitive_systems")):
        base_dir.mkdir(exist_ok=True, parents=True)
        system_dir = base_dir / self.name
        system_dir.mkdir(exist_ok=True)
        
        # Save current state
        with open(system_dir / f"state_{self.history[-1][1]}.json", 'w') as f:
            json.dump({
                'name': self.name,
                'state': self.state,
                'subsystems': list(self.subsystems.keys()),
                'history': self.history,
                'source': self.source
            }, f, indent=2)
        
        # Save subsystems
        for name, subsystem in self.subsystems.items():
            subsystem.save(system_dir / "subsystems")
    
    @classmethod
    def load(cls, name, base_dir=Path("cognitive_systems")):
        system_dir = base_dir / name
        if not system_dir.exists():
            return None
        
        # Find latest state file
        state_files = list(system_dir.glob("state_*.json"))
        if not state_files:
            return None
        
        latest = max(state_files, key=lambda p: p.stat().st_mtime)
        with open(latest, 'r') as f:
            data = json.load(f)
        
        # Create system
        system = cls(name, **data['state'])
        system.history = data['history']
        
        # Load subsystems
        subsystems_dir = system_dir / "subsystems"
        if subsystems_dir.exists():
            for subdir in subsystems_dir.iterdir():
                if subdir.is_dir():
                    subsystem = cls.load(subdir.name, subsystems_dir)
                    if subsystem:
                        system.subsystems[subdir.name] = subsystem
        
        return system

class Cognosis:
    def __init__(self):
        self.root = CognitiveSystem("root", 
                                    architecture="morphological",
                                    version="0.1.0",
                                    created=datetime.now().isoformat())
    
    def bootstrap(self):
        # Create initial cognitive structure
        perception = self.root.add_subsystem(
            "perception", 
            CognitiveSystem("perception", 
                          mode="predictive_processing", 
                          dimensions="adaptive")
        )
        
        action = self.root.add_subsystem(
            "action",
            CognitiveSystem("action",
                         executor="local_llm",
                         endpoint="ollama://localhost:11434")
        )
        
        memory = self.root.add_subsystem(
            "memory",
            CognitiveSystem("memory",
                         storage="distributed",
                         encoding="morphological")
        )
        
        # Initial connections
        perception.update_state(
            inputs=["environment", "action.feedback"],
            outputs=["memory.sensory", "action.stimulus"]
        )
        
        action.update_state(
            inputs=["perception.stimulus", "memory.patterns"],
            outputs=["environment", "perception.feedback"]
        )
        
        memory.update_state(
            inputs=["perception.sensory", "action.results"],
            outputs=["perception.context", "action.patterns"]
        )
        
        # Save initial state
        self.root.save()
        
        return self.root

# Bootstrap the system
if __name__ == "__main__":
    cognosis = Cognosis()
    root_system = cognosis.bootstrap()
    print(f"Bootstrapped Cognosis system with root: {root_system.name}")
    print(f"Initial state hash: {root_system.history[-1][1]}")
    print(f"Subsystems: {list(root_system.subsystems.keys())}")