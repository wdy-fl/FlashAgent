# NodeData.py

from dataclasses import dataclass, asdict, field, fields
from typing import List, Dict

@dataclass
class Serializable:
    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Filter out unknown fields to ensure forward/backward compatibility."""
        known_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

@dataclass
class NodeData(Serializable):

    # Graph Feature
    uniq_id: str = ""

    # Store external properties in a dictionary
    ext: dict = field(default_factory=dict)

    nexts: List[int] = field(default_factory=list)

    # LangGraph attribute
    # "START", "LLM", "ROUTER", "INFO"
    type: str = "START"

    # AGENT
    name: str = ""
    description: str = ""

    # LLM
    tools: List[str] = field(default_factory=list)

    # ROUTER
    branches: Dict[str, str] = field(default_factory=dict)
    max_iterations: int = 0

    # HUMAN_INPUT
    input_schema: dict = field(default_factory=dict)
