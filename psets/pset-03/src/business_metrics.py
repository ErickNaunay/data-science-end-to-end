"""Pairwise uncertainty calibration and explicitly labeled coelution proxies."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def _sample_condition_pairs(
    condition_groups: Sequence[object],
    molecule_groups: Sequence[object],
    *,
    max_pairs: int,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray]:
    conditions = (
        pd.Series(condition_groups).reset_index(drop=True).fillna("<MISSING>").astype(str)
    )
    molecules = (
        pd.Series(molecule_groups).reset_index(drop=True).fillna("<MISSING>").astype(str)
    )
    rng = np.random.default_rng(random_state)
    group_indices = [
        group.index.to_numpy()
        for _, group in conditions.groupby(conditions, sort=True)
        if len(group) > 1
    ]
    if not group_indices:
        raise ValueError("No chromatographic condition has two or more observations")

    left_parts = []
    right_parts = []
    remaining = max_pairs
    pairs_per_group = max(1, max_pairs // len(group_indices))
    for indices in group_indices:
        pair_count = min(pairs_per_group, remaining)
        if len(indices) <= 2_000:
            left_positions, right_positions = np.triu_indices(len(indices), k=1)
            left_values = indices[left_positions]
            right_values = indices[right_positions]
            valid = (
                molecules.iloc[left_values].to_numpy()
                != molecules.iloc[right_values].to_numpy()
            )
            left_values = left_values[valid]
            right_values = right_values[valid]
            if len(left_values) > pair_count:
                selected = rng.choice(len(left_values), size=pair_count, replace=False)
                left_values = left_values[selected]
                right_values = right_values[selected]
        else:
            selected_pairs: set[tuple[int, int]] = set()
            attempts = 0
            while len(selected_pairs) < pair_count and attempts < 20 * pair_count:
                left = int(rng.choice(indices))
                right = int(rng.choice(indices))
                if (
                    left != right
                    and molecules.iloc[left] != molecules.iloc[right]
                ):
                    selected_pairs.add((min(left, right), max(left, right)))
                attempts += 1
            if not selected_pairs:
                continue
            left_values, right_values = map(
                np.asarray, zip(*sorted(selected_pairs), strict=True)
            )
        if len(left_values):
            left_parts.append(left_values)
            right_parts.append(right_values)
            remaining -= len(left_values)
        if remaining <= 0:
            break

    if not left_parts:
        raise ValueError("Could not sample pairs of distinct compounds by condition")
    left = np.concatenate(left_parts)[:max_pairs]
    right = np.concatenate(right_parts)[:max_pairs]
    if len(left) == 0:
        raise ValueError("No distinct-compound pairs were sampled")
    return left.astype(int), right.astype(int)


def calibrate_pairwise_interval(
    y_true: Sequence[float],
    y_oof: Sequence[float],
    condition_groups: Sequence[object],
    molecule_groups: Sequence[object],
    *,
    coverage: float = 0.95,
    max_pairs: int = 100_000,
    random_state: int = 42,
) -> dict[str, float | int]:
    """Estimate a two-sided prediction interval from out-of-fold pair errors."""
    if not 0 < coverage < 1:
        raise ValueError("coverage must be between 0 and 1")
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_oof, dtype=float)
    if not (len(actual) == len(predicted) == len(condition_groups) == len(molecule_groups)):
        raise ValueError("Targets, predictions, and grouping arrays must align")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("OOF targets and predictions must be finite")

    left, right = _sample_condition_pairs(
        condition_groups,
        molecule_groups,
        max_pairs=max_pairs,
        random_state=random_state,
    )
    residual = actual - predicted
    pair_errors = residual[left] - residual[right]
    tail = (1 - coverage) / 2
    lower, upper = np.quantile(pair_errors, [tail, 1 - tail])
    return {
        "coverage": float(coverage),
        "lower_error_quantile": float(lower),
        "upper_error_quantile": float(upper),
        "pair_error_radius": float(max(abs(lower), abs(upper))),
        "calibration_pairs": int(len(pair_errors)),
    }


def coelution_proxy_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    condition_groups: Sequence[object],
    molecule_groups: Sequence[object],
    interval: dict[str, float | int],
    *,
    max_pairs: int = 100_000,
    random_state: int = 42,
) -> dict[str, float | int]:
    """Evaluate near-retention alerts as a proxy, not as confirmed coelution."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if not (len(actual) == len(predicted) == len(condition_groups) == len(molecule_groups)):
        raise ValueError("Targets, predictions, and grouping arrays must align")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Holdout targets and predictions must be finite")

    left, right = _sample_condition_pairs(
        condition_groups,
        molecule_groups,
        max_pairs=max_pairs,
        random_state=random_state,
    )
    observed_delta = actual[left] - actual[right]
    predicted_delta = predicted[left] - predicted[right]
    lower = predicted_delta + float(interval["lower_error_quantile"])
    upper = predicted_delta + float(interval["upper_error_quantile"])
    alerts = (lower <= 0) & (upper >= 0)
    radius = float(interval["pair_error_radius"])
    near_retention_proxy = np.abs(observed_delta) <= radius
    near_count = int(near_retention_proxy.sum())
    recall = (
        float(alerts[near_retention_proxy].mean())
        if near_count
        else float("nan")
    )
    coverage = ((observed_delta >= lower) & (observed_delta <= upper)).mean()
    return {
        "comparison_pairs": int(len(left)),
        "near_retention_proxy_pairs": near_count,
        "coelution_proxy_recall": recall,
        "coelution_proxy_false_negative_rate": (
            1.0 - recall if np.isfinite(recall) else float("nan")
        ),
        "potential_coelution_alert_rate": float(alerts.mean()),
        "pairwise_prediction_interval_coverage": float(coverage),
        "coelution_labels_are_proxy": 1,
    }
