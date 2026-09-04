"""HTTP transport. Routing and serialization only — no domain logic."""

from kavi.api.routes import Router, build_router  # noqa: F401

__all__ = ["Router", "build_router"]
