"""Workspace contract: a project is a directory."""
from qrest_agent.workspace.project import (
    ProjectError,
    find_project_root,
    init_project,
    read_parse_state,
    read_project_json,
    write_parse_state,
)
from qrest_agent.workspace.index import update_index

__all__ = [
    "ProjectError",
    "find_project_root",
    "init_project",
    "read_project_json",
    "read_parse_state",
    "write_parse_state",
    "update_index",
]
