"""
R5 Operational Intelligence Platform - Phase 20: Mathematical & Statistical Metric Calculators
Provides pure, reproducible calculation of evaluation metrics across all 12 dimensions.
"""

from typing import List, Dict, Any, Tuple, Set


def compute_accuracy(y_true: List[Any], y_pred: List[Any]) -> float:
    """Compute simple classification accuracy between true and predicted lists."""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    matches = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return round(matches / len(y_true), 4)


def compute_classification_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, float]:
    """
    Compute Accuracy, Macro Precision, Macro Recall, and Macro F1
    for multi-class categorization.
    """
    if not y_true or len(y_true) != len(y_pred):
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    classes = sorted(list(set(y_true) | set(y_pred)))
    precisions = []
    recalls = []

    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)

    macro_precision = sum(precisions) / len(precisions) if precisions else 0.0
    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = (
        (2 * macro_precision * macro_recall) / (macro_precision + macro_recall)
        if (macro_precision + macro_recall) > 0
        else 0.0
    )
    accuracy = compute_accuracy(y_true, y_pred)

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(macro_precision, 4),
        "recall": round(macro_recall, 4),
        "f1": round(macro_f1, 4),
    }


def compute_token_overlap_f1(truth_tokens: Set[str], pred_tokens: Set[str]) -> float:
    """Compute token-level precision, recall, and F1 between two sets of strings."""
    if not truth_tokens and not pred_tokens:
        return 1.0
    if not truth_tokens or not pred_tokens:
        return 0.0

    intersection = truth_tokens.intersection(pred_tokens)
    prec = len(intersection) / len(pred_tokens)
    rec = len(intersection) / len(truth_tokens)

    if prec + rec == 0.0:
        return 0.0
    return round((2 * prec * rec) / (prec + rec), 4)


def compute_entity_overlap_f1(true_entities: List[str], pred_entities: List[str]) -> float:
    """Compute case-insensitive entity overlap F1 score across entity mentions."""
    true_set = {e.strip().lower() for e in true_entities if e and e.strip()}
    pred_set = {e.strip().lower() for e in pred_entities if e and e.strip()}
    return compute_token_overlap_f1(true_set, pred_set)


def compute_cluster_purity(
    predicted_clusters: Dict[str, List[str]],
    ground_truth_assignments: Dict[str, str]
) -> float:
    """
    Compute clustering purity:
    Purity = (1 / N) * sum_k max_j |c_k intersect t_j|
    Where c_k is predicted cluster, t_j is ground truth class.
    """
    total_items = len(ground_truth_assignments)
    if total_items == 0 or not predicted_clusters:
        return 0.0

    purity_sum = 0
    for cluster_id, item_ids in predicted_clusters.items():
        if not item_ids:
            continue
        # Count occurrences of each true label in this predicted cluster
        label_counts: Dict[str, int] = {}
        for item_id in item_ids:
            true_label = ground_truth_assignments.get(item_id)
            if true_label is not None:
                label_counts[true_label] = label_counts.get(true_label, 0) + 1

        if label_counts:
            purity_sum += max(label_counts.values())

    return round(purity_sum / total_items, 4)


def compute_rand_index(
    predicted_clusters: Dict[str, List[str]],
    ground_truth_assignments: Dict[str, str]
) -> float:
    """
    Compute Pairwise Rand Index:
    RI = (a + b) / (a + b + c + d)
    a: pairs in same cluster in both
    b: pairs in different clusters in both
    c: pairs in same cluster in pred, different in true
    d: pairs in different clusters in pred, same in true
    """
    item_ids = list(ground_truth_assignments.keys())
    n = len(item_ids)
    if n < 2:
        return 1.0

    # Build pred_assignment mapping
    pred_assignments: Dict[str, str] = {}
    for c_id, ids in predicted_clusters.items():
        for i_id in ids:
            pred_assignments[i_id] = c_id

    a = 0
    b = 0
    c = 0
    d = 0

    for i in range(n):
        for j in range(i + 1, n):
            id_i, id_j = item_ids[i], item_ids[j]
            same_true = (ground_truth_assignments[id_i] == ground_truth_assignments[id_j])
            same_pred = (pred_assignments.get(id_i) == pred_assignments.get(id_j))

            if same_true and same_pred:
                a += 1
            elif not same_true and not same_pred:
                b += 1
            elif not same_true and same_pred:
                c += 1
            elif same_true and not same_pred:
                d += 1

    total_pairs = a + b + c + d
    if total_pairs == 0:
        return 1.0
    return round((a + b) / total_pairs, 4)


def compute_cross_cluster_leakage_rate(
    predicted_clusters: Dict[str, List[str]],
    ground_truth_assignments: Dict[str, str]
) -> float:
    """
    Compute cross-cluster leakage:
    Rate of items placed in the same cluster that actually belong to different ground truth topics.
    """
    item_ids = list(ground_truth_assignments.keys())
    n = len(item_ids)
    if n < 2:
        return 0.0

    pred_assignments: Dict[str, str] = {}
    for c_id, ids in predicted_clusters.items():
        for i_id in ids:
            pred_assignments[i_id] = c_id

    unrelated_merged = 0
    total_unrelated_pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            id_i, id_j = item_ids[i], item_ids[j]
            if ground_truth_assignments[id_i] != ground_truth_assignments[id_j]:
                total_unrelated_pairs += 1
                if pred_assignments.get(id_i) == pred_assignments.get(id_j):
                    unrelated_merged += 1

    if total_unrelated_pairs == 0:
        return 0.0
    return round(unrelated_merged / total_unrelated_pairs, 4)


def compute_monotonicity_compliance(pairs: List[Tuple[float, float]]) -> float:
    """
    Given a list of (true_severity_higher, true_severity_lower),
    computes what fraction satisfies pred_score(higher) >= pred_score(lower).
    """
    if not pairs:
        return 1.0
    valid = sum(1 for higher, lower in pairs if higher >= lower)
    return round(valid / len(pairs), 4)


def compute_detection_sensitivity(true_positives: int, false_negatives: int) -> float:
    """Compute True Positive Rate (Sensitivity / Recall)."""
    total = true_positives + false_negatives
    if total == 0:
        return 1.0
    return round(true_positives / total, 4)


def compute_false_alert_rate(false_positives: int, true_negatives: int) -> float:
    """Compute False Positive Rate (FPR): FP / (FP + TN)."""
    total = false_positives + true_negatives
    if total == 0:
        return 0.0
    return round(false_positives / total, 4)


def compute_grounding_ratio(
    verified_citations: int,
    total_claims: int
) -> float:
    """Compute ratio of claims supported by valid evidence citations."""
    if total_claims == 0:
        return 1.0
    return round(verified_citations / total_claims, 4)


def compute_hallucination_rate(
    unsupported_entities_count: int,
    total_extracted_entities: int
) -> float:
    """
    Compute hallucination rate:
    Fraction of extracted entities that have no verbatim or semantic grounding in the source input.
    """
    if total_extracted_entities == 0:
        return 0.0
    return round(unsupported_entities_count / total_extracted_entities, 4)
