import os
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, List, Any

@dataclass
class Affordance:
    """Represents a single executable action or trigger."""
    name: str
    type: str  # e.g., 'text_parser', 'system_action'
    params: Dict[str, Any]

class AffordanceManager:
    """Manages affordances that can be triggered by the Heartbeat's reasoning."""
    def __init__(self, affordances_path: str = "automation/affordances.json"):
        self.affordances_path = Path(affordances_path)
        self.affordances: Dict[str, Affordance] = {}
        self.affordances_path.parent.mkdir(parents=True, exist_ok=True)
        self.load_affordances()

    def load_affordances(self):
        """
        Loads affordances from the JSON file.
        Includes backward compatibility for the old format.
        """
        if not self.affordances_path.exists():
            self.affordances = {}
            return

        needs_resave = False
        try:
            with open(self.affordances_path, 'r', encoding='utf-8') as f:
                # Handle empty file case
                content = f.read()
                if not content:
                    affordances_data = {}
                else:
                    affordances_data = json.loads(content)

            migrated_affordances = {}
            for name, data in affordances_data.items():
                if "type" not in data: # Old format detection
                    needs_resave = True
                    params = {
                        "start_trigger": data.get("start_trigger", ""),
                        "end_trigger": data.get("end_trigger", ""),
                        "output_path": data.get("output_path", ""),
                        "output_filename": data.get("output_filename", "")
                    }
                    migrated_affordances[name] = Affordance(
                        name=data.get("name", name),
                        type="text_parser",
                        params=params
                    )
                else: # New format
                     migrated_affordances[name] = Affordance(**data)

            self.affordances = migrated_affordances

            if needs_resave:
                print("Old affordance format detected, migrating and resaving.")
                self.save_affordances()

        except (json.JSONDecodeError, IOError, TypeError) as e:
            print(f"Error loading or migrating affordances: {e}")
            self.affordances = {}

    def save_affordances(self):
        """Saves all current affordances to the JSON file in the new format."""
        try:
            # Use asdict to properly serialize the dataclass, including nested dicts
            affordances_data = {name: asdict(affordance) for name, affordance in self.affordances.items()}
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
