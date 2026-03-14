from dataclasses import dataclass, asdict
from typing import Any
import json
import yaml


@dataclass
class OutputEnvelope:
    """Structured output envelope for AI agent consumption."""

    ok: bool
    data: Any
    schema_version: str = "1"
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), allow_unicode=True, default_flow_style=False)
