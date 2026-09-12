from __future__ import annotations

import pytest

from base_projects.workspace_test import (
    WorkspaceTestSelectionError, WorkspaceTestTarget, select_workspace_test_targets,
)


def target(root, name, project_name):
    return WorkspaceTestTarget(
        name=name, root=root, manifest_path=root / "base_manifest.yaml", project_name=project_name, action="test",
    )


def test_repository_name_selects_exact_target_before_matching_project_names(tmp_path):
    intended = target(tmp_path / "demo", "demo", "demo")
    other = target(tmp_path / "other", "other", "demo")

    assert select_workspace_test_targets((intended, other), "demo") == (intended,)


def test_ambiguous_project_name_requires_repository_selector(tmp_path):
    targets = (target(tmp_path / "first", "first", "shared"), target(tmp_path / "second", "second", "shared"))

    with pytest.raises(WorkspaceTestSelectionError, match="ambiguous"):
        select_workspace_test_targets(targets, "shared")
    assert select_workspace_test_targets(targets, "first") == (targets[0],)
    assert select_workspace_test_targets(targets, None) == targets


@pytest.mark.parametrize("selector", [None, "first,alias"])
def test_aliases_of_same_manifest_cannot_be_selected_twice(tmp_path, selector):
    root = tmp_path / "first"
    root.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    targets = (target(root, "first", "demo"), target(alias, "alias", "demo"))

    with pytest.raises(WorkspaceTestSelectionError, match="same manifest"):
        select_workspace_test_targets(targets, selector)
    assert select_workspace_test_targets(targets, "alias") == (targets[1],)
