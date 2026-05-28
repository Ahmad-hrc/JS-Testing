"""Rollout Initiative Registry — maps rollout names to document source configs."""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)

EXPECTED_DOC_TYPES = [
    "project_plan",
    "training_material",
    "change_management",
    "comms_plan",
    "go_live_checklist",
]


@dataclass
class DocumentSource:
    type: str  # "sharepoint" | "local"
    connection: dict[str, Any]
    doc_type_hints: list[str] = field(default_factory=list)


@dataclass
class RolloutInitiative:
    name: str
    sources: list[DocumentSource] = field(default_factory=list)
    doc_count: int = 0


class RolloutRegistry:
    """Maps rollout initiative names to document source configurations."""

    def __init__(self) -> None:
        self._initiatives: dict[str, RolloutInitiative] = {}

    def register(self, initiative: RolloutInitiative) -> None:
        self._initiatives[initiative.name] = initiative
        logger.info("Registered rollout initiative: %s", initiative.name)

    def get(self, name: str) -> RolloutInitiative | None:
        return self._initiatives.get(name)

    def all_names(self) -> list[str]:
        return list(self._initiatives.keys())

    def update_doc_count(self, name: str, count: int) -> None:
        if name in self._initiatives:
            self._initiatives[name].doc_count = count

    def load_from_yaml(self, path: str) -> None:
        if not os.path.exists(path):
            logger.warning("rollout_config.yaml not found at %s — starting with empty registry", path)
            return
        with open(path) as f:
            data = yaml.safe_load(f)
        for item in data.get("rollouts", []):
            sources = [
                DocumentSource(
                    type=s.get("type", "local"),
                    connection=s.get("connection", {}),
                    doc_type_hints=s.get("doc_type_hints", []),
                )
                for s in item.get("sources", [])
            ]
            self.register(RolloutInitiative(name=item["name"], sources=sources))


# Shared singleton
_registry: RolloutRegistry | None = None


def get_registry() -> RolloutRegistry:
    global _registry
    if _registry is None:
        _registry = RolloutRegistry()
        config_path = os.environ.get("ROLLOUT_CONFIG_PATH", "rollout_config.yaml")
        _registry.load_from_yaml(config_path)
    return _registry


def reset_registry() -> None:
    """Reset the singleton — for tests only."""
    global _registry
    _registry = None
