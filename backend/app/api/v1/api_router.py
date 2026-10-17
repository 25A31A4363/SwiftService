from fastapi import APIRouter
from backend.app.api.v1.auth_router import router as auth_router
from backend.app.api.v1.hierarchy_router import router as hierarchy_router
from backend.app.api.v1.users_router import router as users_router
from backend.app.api.v1.roles_router import router as roles_router
from backend.app.api.v1.ownership_router import router as ownership_router
from backend.app.api.v1.feedback_router import router as feedback_router
from backend.app.api.v1.investigation_router import router as investigation_router
from backend.app.api.v1.clusters_router import router as clusters_router
from backend.app.api.v1.lineage_router import router as lineage_router
from backend.app.api.v1.issues_router import router as issues_router
from backend.app.api.v1.routing_router import router as routing_router
from backend.app.api.v1.alerts_router import router as alerts_router
from backend.app.api.v1.actions_router import router as actions_router
from backend.app.api.v1.resolutions_router import router as resolutions_router
from backend.app.api.v1.outcomes_router import router as outcomes_router
from backend.app.api.v1.briefs_router import router as briefs_router
from backend.app.api.v1.audit_router import router as audit_router
from backend.app.api.v1.health_router import router as health_router
from backend.app.api.v1.personal_home_router import router as personal_home_router
from backend.app.api.v1.multilingual_router import router as multilingual_router
from backend.app.api.v1.security_router import router as security_router
from backend.app.api.v1.observability_router import router as observability_router
from backend.app.api.v1.jobs_router import router as jobs_router
from backend.app.api.v1.evaluation_router import router as evaluation_router
from backend.app.api.v1.demo_router import router as demo_router
from backend.app.api.v1.complaints_router import router as complaints_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(hierarchy_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(roles_router)
api_v1_router.include_router(ownership_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(clusters_router)
api_v1_router.include_router(lineage_router)
api_v1_router.include_router(issues_router)
api_v1_router.include_router(routing_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(actions_router)
api_v1_router.include_router(resolutions_router)
api_v1_router.include_router(outcomes_router)
api_v1_router.include_router(briefs_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(personal_home_router)
api_v1_router.include_router(multilingual_router)
api_v1_router.include_router(security_router, prefix="/security", tags=["Security & AI Governance"])
api_v1_router.include_router(observability_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(evaluation_router)
api_v1_router.include_router(demo_router)
api_v1_router.include_router(complaints_router)


