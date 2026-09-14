"""Float literals and bounded regression-tree parsing for C export."""

from __future__ import annotations

import re
from typing import Any

MAX_DEPTH = 3
MAX_NODES = 2 ** (MAX_DEPTH + 1) - 1


def _c_float(value: float) -> str:
    literal = f"{float(value):.9g}"
    if "." not in literal and "e" not in literal.lower():
        literal += ".0"
    return literal + "f"


def _tree_depth(node: dict[str, Any]) -> int:
    if "leaf" in node:
        return 0
    return 1 + max(_tree_depth(child) for child in node.get("children", []))


def _parse_tree(tree: dict[str, Any], feature_names: list[str]) -> list[dict[str, Any]]:
    """Flatten an XGBoost JSON tree while preserving yes/no/missing branches."""
    nodes: list[dict[str, Any]] = []

    def feature_index(split: str) -> int:
        if split in feature_names:
            return feature_names.index(split)
        match = re.fullmatch(r"f(\d+)", split)
        if not match:
            raise ValueError(f"Unknown XGBoost split feature {split!r}")
        index = int(match.group(1))
        if index >= len(feature_names):
            raise ValueError(
                f"Tree references feature {index}, but this head has {len(feature_names)} features"
            )
        return index

    def visit(node: dict[str, Any]) -> int:
        if len(nodes) >= MAX_NODES:
            raise ValueError(
                f"Tree exceeds the depth-{MAX_DEPTH} node budget of {MAX_NODES}"
            )
        current = len(nodes)
        if "leaf" in node:
            nodes.append(
                {
                    "feature_index": -1,
                    "threshold": 0.0,
                    "left_child": -1,
                    "right_child": -1,
                    "missing_child": -1,
                    "leaf_value": float(node["leaf"]),
                }
            )
            return current

        nodes.append({})
        children = {int(child["nodeid"]): child for child in node.get("children", [])}
        yes_id = int(node["yes"])
        no_id = int(node["no"])
        if yes_id not in children or no_id not in children:
            raise ValueError("XGBoost dump is missing a declared yes/no child")
        left_child = visit(children[yes_id])
        right_child = visit(children[no_id])
        missing_id = int(node.get("missing", yes_id))
        if missing_id not in (yes_id, no_id):
            raise ValueError("XGBoost missing branch is not one of the yes/no children")
        nodes[current] = {
            "feature_index": feature_index(str(node["split"])),
            "threshold": float(node["split_condition"]),
            "left_child": left_child,
            "right_child": right_child,
            "missing_child": left_child if missing_id == yes_id else right_child,
            "leaf_value": 0.0,
        }
        return current

    visit(tree)
    return nodes
