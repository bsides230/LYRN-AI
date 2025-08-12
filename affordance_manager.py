import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List

@dataclass
class Affordance:
    """Represents a single internal-only job called an Affordance."""
    name: str
    start_trigger: str
    end_trigger: str
    output_path: str
    output_filename: str

class AffordanceManager:
    """Manages affordances that can be triggered by the Heartbeat's reasoning."""
    def __init__(self, affordances_path: str = "automation/affordances.json"):
        self.affordances_path = Path(affordances_path)
        self.affordances: Dict[str, Affordance] = {}
        self.affordances_path.parent.mkdir(parents=True, exist_ok=True)
        self.load_affordances()

    def load_affordances(self):
        """Loads affordances from the JSON file."""
        if not self.affordances_path.exists():
            self.affordances = {}
            return

        try:
            with open(self.affordances_path, 'r', encoding='utf-8') as f:
                affordances_data = json.load(f)
                for name, data in affordances_data.items():
                    self.affordances[name] = Affordance(**data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading affordances: {e}")
            self.affordances = {}

    def save_affordances(self):
        """Saves all current affordances to the JSON file."""
        try:
            affordances_data = {name: affordance.__dict__ for name, affordance in self.affordances.items()}
            with open(self.affordances_path, 'w', encoding='utf-8') as f:
                json.dump(affordances_data, f, indent=2)
        except IOError as e:
            print(f"Error saving affordances: {e}")

    def add_affordance(self, affordance: Affordance):
        """Adds or updates an affordance."""
        self.affordances[affordance.name] = affordance
        self.save_affordances()

    def delete_affordance(self, affordance_name: str):
        """Deletes an affordance."""
        if affordance_name in self.affordances:
            del self.affordances[affordance_name]
            self.save_affordances()

    def get_affordance(self, affordance_name: str) -> Optional[Affordance]:
        """Retrieves a single affordance by name."""
        return self.affordances.get(affordance_name)

    def get_all_affordances(self) -> List[Affordance]:
        """Returns a list of all affordances."""
        return list(self.affordances.values())
