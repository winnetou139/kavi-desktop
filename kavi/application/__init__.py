"""Application layer: use cases. Orchestrates domain + infrastructure."""

from kavi.application.services import CockpitService  # noqa: F401

__all__ = ["CockpitService"]
