"""Deterministic maximum-cardinality bipartite matching for one-to-one defect consumption."""

from collections.abc import Callable
from typing import TypeVar

T_Pred = TypeVar("T_Pred")
T_Defect = TypeVar("T_Defect")


def find_maximum_bipartite_matching[T_Pred, T_Defect](
    predictions: list[T_Pred],
    defects: list[T_Defect],
    can_match: Callable[[T_Pred, T_Defect], bool],
    match_priority: Callable[[T_Pred, T_Defect], tuple] | None = None,
) -> dict[int, int]:
    """Compute maximum-cardinality bipartite matching between predictions and defects.

    Guarantees:
    1. One-to-one consumption: Each defect matches at most one prediction; each prediction matches at most one defect.
    2. Maximum cardinality: Maximizes the total number of True Positive pairs.
    3. Input order independence: Candidate lists are indexed, and adjacency lists are deterministically sorted.

    Args:
        predictions: List of candidate predictions.
        defects: List of ground-truth defects.
        can_match: Predicate returning True if prediction i can match defect j.
        match_priority: Optional priority tuple for tie-breaking candidate edges (higher priority first).

    Returns:
        Mapping of prediction index -> defect index for matched pairs.
    """
    n_preds = len(predictions)
    n_defects = len(defects)

    if n_preds == 0 or n_defects == 0:
        return {}

    # Build adjacency list: pred_idx -> list of defect_idx
    adj: dict[int, list[int]] = {}
    for i, p in enumerate(predictions):
        edges = []
        for j, d in enumerate(defects):
            if can_match(p, d):
                priority = match_priority(p, d) if match_priority else (0,)
                edges.append((priority, j))

        # Sort candidates deterministically: highest priority first, then smallest defect index
        def edge_sort_key(item: tuple) -> tuple:
            p, j = item
            if isinstance(p, tuple):
                neg_p = tuple(-x if isinstance(x, (int, float)) else x for x in p)
                return (neg_p, j)
            elif isinstance(p, (int, float)):
                return (-p, j)
            return (p, j)

        edges.sort(key=edge_sort_key)
        adj[i] = [j for _, j in edges]

    # Kuhn's algorithm for Maximum Bipartite Matching with deterministic augmenting paths
    defect_match: dict[int, int] = {}  # defect_idx -> pred_idx

    def dfs(u: int, visited: list[bool]) -> bool:
        for v in adj.get(u, []):
            if not visited[v]:
                visited[v] = True
                # If defect v is not matched or previously matched pred can be rematched
                if v not in defect_match or dfs(defect_match[v], visited):
                    defect_match[v] = u
                    return True
        return False

    # Process predictions in index order
    for u in range(n_preds):
        visited = [False] * n_defects
        dfs(u, visited)

    # Invert mapping to pred_idx -> defect_idx
    pred_match = {pred_idx: defect_idx for defect_idx, pred_idx in defect_match.items()}
    return pred_match
