from __future__ import annotations


class ProjectDiscoveryError(RuntimeError):
    pass


class ProjectNotFoundError(ProjectDiscoveryError):
    pass
