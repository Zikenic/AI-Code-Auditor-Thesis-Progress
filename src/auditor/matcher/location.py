"""Range-based location matching logic with locked +-10 lines tolerance window."""

TOLERANCE_WINDOW_LINES: int = 10


def has_direct_overlap(
    gt_start: int,
    gt_end: int,
    pred_start: int,
    pred_end: int,
) -> bool:
    """Return True if predicted range and ground-truth range have a non-empty intersection."""
    return max(gt_start, pred_start) <= min(gt_end, pred_end)


def matches_tolerance_window(
    gt_start: int,
    gt_end: int,
    pred_start: int,
    pred_end: int,
    tolerance: int = TOLERANCE_WINDOW_LINES,
) -> bool:
    """Return True if predicted range intersects the ground-truth +-10 lines tolerance window.

    Tolerance window definition:
        Window = [max(gt_start - tolerance, 1), gt_end + tolerance]

    Intersection condition:
        max(window_start, pred_start) <= min(window_end, pred_end)
    """
    window_start = max(gt_start - tolerance, 1)
    window_end = gt_end + tolerance
    return max(window_start, pred_start) <= min(window_end, pred_end)


def check_location_match(
    gt_start: int,
    gt_end: int,
    pred_start: int | None,
    pred_end: int | None,
    tolerance: int = TOLERANCE_WINDOW_LINES,
) -> tuple[bool, bool]:
    """Evaluate location match between ground-truth defect and predicted finding.

    Args:
        gt_start: 1-indexed ground-truth start line (>= 1).
        gt_end: 1-indexed ground-truth end line (>= gt_start).
        pred_start: Predicted start line or None.
        pred_end: Predicted end line or None.
        tolerance: Uniform line tolerance (default 10 lines).

    Returns:
        (is_matched, is_direct_overlap)
        - is_matched: True if predicted range intersects the tolerance window.
        - is_direct_overlap: True if predicted range has direct line overlap with GT.
    """
    # Findings without usable line coordinates cannot satisfy locus match
    if pred_start is None or pred_end is None:
        return False, False

    if pred_start < 1 or pred_end < pred_start:
        return False, False

    direct = has_direct_overlap(gt_start, gt_end, pred_start, pred_end)
    matched = matches_tolerance_window(gt_start, gt_end, pred_start, pred_end, tolerance)

    return matched, direct
