from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class PromptValidationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="Prompt text to inspect and sanitize")

class PromptValidationResponse(BaseModel):
    isInjection: bool
    riskScore: float
    flaggedPatterns: List[str]
    sanitizedPrompt: str
    piiRedactedPrompt: str
    piiCount: int
    piiCategories: List[str]

class AIExecuteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    providerName: Optional[str] = Field("LOCAL_DETERMINISTIC", description="LOCAL_DETERMINISTIC | EXTERNAL_ENTERPRISE_LLM")
    context: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class AIOverrideRequest(BaseModel):
    governanceLogId: str = Field(..., min_length=3)
    overrideReason: str = Field(..., min_length=5, description="Human justification for overriding the AI decision")
    newConfidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    notes: Optional[str] = None

class RetentionPolicyRequest(BaseModel):
    entityType: str = Field(..., description="FEEDBACK_ITEMS | INVESTIGATION_QUESTIONS | ALERTS | ACTION_PLANS | AUDIT_LOGS")
    retentionDays: int = Field(..., ge=1, le=3650)
    actionOnExpire: str = Field("PURGE", description="PURGE | ANONYMIZE")
    isActive: bool = True

class RetentionPurgeRequest(BaseModel):
    dryRun: bool = False
