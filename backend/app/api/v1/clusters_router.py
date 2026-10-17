import sqlite3
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query

from backend.app.db.database import get_db
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission
from backend.app.schemas.domain import (
    ClusterResponse,
    ClusterCreateRequest,
    ClusterMergeRequest,
    ClusterSplitRequest,
    ClusterUpdateRequest
)
from backend.app.services.clustering_service import ClusteringService

router = APIRouter(prefix="/clusters", tags=["Phase 6: Cross-Source Semantic Clustering"])

@router.get("", response_model=List[ClusterResponse])
def list_clusters(
    storeId: Optional[str] = Query(None),
    status: Optional[str] = Query("ACTIVE"),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.ISSUE_READ))
):
    """List semantic issue clusters with member feedback counts and quality scores."""
    return ClusteringService.list_clusters(
        conn=conn,
        organization_id=user["organizationId"],
        store_id=storeId,
        status=status,
        limit=limit
    )

@router.get("/{cluster_id}", response_model=ClusterResponse)
def get_cluster(
    cluster_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.ISSUE_READ))
):
    """Retrieve cluster details, member feedback citations, and quality metrics."""
    return ClusteringService.get_cluster_details(conn, cluster_id)

@router.post("/discover", response_model=List[ClusterResponse])
def discover_clusters(
    payload: Optional[ClusterCreateRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    """
    Run cross-source semantic clustering on recent feedback.
    Synthesizes grounded clusters based strictly on empirical evidence.
    """
    store_id = payload.storeId if payload else None
    hours = payload.timeWindowHours if (payload and payload.timeWindowHours) else 72
    threshold = payload.similarityThreshold if (payload and payload.similarityThreshold) else 0.65

    return ClusteringService.discover_and_cluster_feedback(
        conn=conn,
        organization_id=user["organizationId"],
        store_id=store_id,
        time_window_hours=hours,
        similarity_threshold=threshold,
        user_id=user["id"]
    )

@router.post("/merge", response_model=ClusterResponse)
def merge_clusters(
    payload: ClusterMergeRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    """Human operator merges two related clusters into one primary cluster."""
    return ClusteringService.merge_clusters(
        conn=conn,
        primary_cluster_id=payload.primaryClusterId,
        secondary_cluster_id=payload.secondaryClusterId,
        merged_title=payload.mergedTitle,
        justification=payload.justification,
        user_id=user["id"]
    )

@router.post("/{cluster_id}/split", response_model=ClusterResponse)
def split_cluster(
    cluster_id: str,
    payload: ClusterSplitRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    """Human operator splits a cluster by segregating specified member feedback items."""
    return ClusteringService.split_cluster(
        conn=conn,
        cluster_id=cluster_id,
        feedback_ids_to_eject=payload.feedbackItemIdsToEject,
        new_cluster_title=payload.newClusterTitle,
        justification=payload.justification,
        user_id=user["id"]
    )

@router.patch("/{cluster_id}", response_model=ClusterResponse)
def update_cluster(
    cluster_id: str,
    payload: ClusterUpdateRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    """Human operator updates cluster title, category, or physical entity."""
    return ClusteringService.update_cluster(
        conn=conn,
        cluster_id=cluster_id,
        title=payload.title,
        category=payload.category,
        primary_location=payload.primaryLocation,
        primary_entity=payload.primaryEntity,
        user_id=user["id"]
    )
