from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# 1. Hierarchy Schemas
class OrganizationResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    regionCount: Optional[int] = 0
    storeCount: Optional[int] = 0
    createdAt: str
    updatedAt: str

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = None
    status: Optional[str] = "ACTIVE"

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = None
    status: Optional[str] = None

class RegionResponse(BaseModel):
    id: str
    organizationId: str
    name: str
    code: str
    description: Optional[str] = None
    leadUserId: Optional[str] = None
    leadUserName: Optional[str] = None
    storeCount: Optional[int] = 0
    createdAt: str
    updatedAt: str

class RegionCreate(BaseModel):
    organizationId: str
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = None
    leadUserId: Optional[str] = None

class RegionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = None
    leadUserId: Optional[str] = None

class StoreAddress(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None

class StoreResponse(BaseModel):
    id: str
    organizationId: str
    regionId: str
    regionName: Optional[str] = None
    name: str
    storeNumber: int
    address: StoreAddress
    timezone: str
    operatingStatus: str = "OPERATIONAL"
    metadata: Optional[Dict[str, Any]] = None
    createdAt: str
    updatedAt: str

class StoreCreate(BaseModel):
    organizationId: str
    regionId: str
    name: str = Field(..., min_length=2, max_length=150)
    storeNumber: int = Field(..., ge=1, le=999999)
    address: Optional[StoreAddress] = None
    timezone: Optional[str] = "UTC"
    operatingStatus: Optional[str] = Field("OPERATIONAL", pattern=r"^(OPERATIONAL|MAINTENANCE_HOLD|RENOVATION|TEMPORARILY_CLOSED|DECOMMISSIONED)$")
    metadata: Optional[Dict[str, Any]] = None

class StoreUpdate(BaseModel):
    regionId: Optional[str] = None
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    storeNumber: Optional[int] = Field(None, ge=1, le=999999)
    address: Optional[StoreAddress] = None
    timezone: Optional[str] = None
    operatingStatus: Optional[str] = Field(None, pattern=r"^(OPERATIONAL|MAINTENANCE_HOLD|RENOVATION|TEMPORARILY_CLOSED|DECOMMISSIONED)$")
    metadata: Optional[Dict[str, Any]] = None

class StoreStatusUpdate(BaseModel):
    operatingStatus: str = Field(..., pattern=r"^(OPERATIONAL|MAINTENANCE_HOLD|RENOVATION|TEMPORARILY_CLOSED|DECOMMISSIONED)$")
    justification: Optional[str] = Field(None, min_length=3)

class DepartmentResponse(BaseModel):
    id: str
    organizationId: str
    storeId: str
    name: str
    floorZone: Optional[str] = None
    createdAt: str
    updatedAt: str

class AssetResponse(BaseModel):
    id: str
    organizationId: str
    storeId: str
    departmentId: Optional[str] = None
    name: str
    assetTag: str
    category: str
    status: str
    metadata: Optional[Dict[str, Any]] = None
    createdAt: str
    updatedAt: str

# 2. Team Schemas
class OperationalTeamResponse(BaseModel):
    id: str
    organizationId: str
    regionId: Optional[str] = None
    regionName: Optional[str] = None
    storeId: Optional[str] = None
    storeName: Optional[str] = None
    name: str
    teamType: str
    slaTier: str
    contactEmail: Optional[str] = None
    responsibility: Optional[str] = None
    specialization: Optional[str] = None
    escalationContact: Optional[str] = None
    escalationTier: Optional[str] = "TIER_1"
    leadUserId: Optional[str] = None
    leadUserName: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    memberCount: Optional[int] = 0
    createdAt: str
    updatedAt: str

class OperationalTeamCreate(BaseModel):
    organizationId: str
    regionId: Optional[str] = None
    storeId: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=150)
    teamType: str = Field(..., min_length=2, max_length=50)
    slaTier: Optional[str] = "STANDARD"
    contactEmail: Optional[str] = None
    responsibility: Optional[str] = None
    specialization: Optional[str] = None
    escalationContact: Optional[str] = None
    escalationTier: Optional[str] = "TIER_1"
    leadUserId: Optional[str] = None
    status: Optional[str] = "ACTIVE"

class OperationalTeamUpdate(BaseModel):
    regionId: Optional[str] = None
    storeId: Optional[str] = None
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    teamType: Optional[str] = Field(None, min_length=2, max_length=50)
    slaTier: Optional[str] = None
    contactEmail: Optional[str] = None
    responsibility: Optional[str] = None
    specialization: Optional[str] = None
    escalationContact: Optional[str] = None
    escalationTier: Optional[str] = None
    leadUserId: Optional[str] = None
    status: Optional[str] = None

class TeamMemberResponse(BaseModel):
    id: str
    teamId: str
    teamName: Optional[str] = None
    userId: str
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    userRole: Optional[str] = None
    roleInTeam: str
    isPrimary: bool
    createdAt: str

class TeamMemberCreate(BaseModel):
    userId: str
    roleInTeam: Optional[str] = "MEMBER"
    isPrimary: Optional[bool] = True

# 2b. Role & Permissions Schemas
class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    isSystem: bool
    permissions: List[str] = []
    userCount: Optional[int] = 0
    createdAt: str
    updatedAt: str

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    description: Optional[str] = None
    permissions: List[str] = []

class RolePermissionsUpdate(BaseModel):
    permissions: List[str] = []

class RolePermissionsMatrixResponse(BaseModel):
    roles: List[RoleResponse]
    allPermissions: List[Dict[str, str]]

# 2c. Operational Ownership & Lineage Tracing Schemas
class OperationalOwnershipMappingResponse(BaseModel):
    id: str
    organizationId: str
    regionId: Optional[str] = None
    regionName: Optional[str] = None
    storeId: Optional[str] = None
    storeName: Optional[str] = None
    departmentId: Optional[str] = None
    departmentName: Optional[str] = None
    operationalDomain: str
    primaryTeamId: str
    primaryTeamName: Optional[str] = None
    secondaryTeamId: Optional[str] = None
    secondaryTeamName: Optional[str] = None
    escalationUserId: Optional[str] = None
    escalationUserName: Optional[str] = None
    slaMinutes: int
    autoEscalateHours: float
    description: Optional[str] = None
    createdAt: str
    updatedAt: str

class OperationalOwnershipMappingCreate(BaseModel):
    organizationId: str
    regionId: Optional[str] = None
    storeId: Optional[str] = None
    departmentId: Optional[str] = None
    operationalDomain: str = Field(..., min_length=2, max_length=80)
    primaryTeamId: str
    secondaryTeamId: Optional[str] = None
    escalationUserId: Optional[str] = None
    slaMinutes: Optional[int] = Field(60, ge=5, le=10080)
    autoEscalateHours: Optional[float] = Field(4.0, ge=0.5, le=168.0)
    description: Optional[str] = None

class OperationalOwnershipMappingUpdate(BaseModel):
    regionId: Optional[str] = None
    storeId: Optional[str] = None
    departmentId: Optional[str] = None
    operationalDomain: Optional[str] = Field(None, min_length=2, max_length=80)
    primaryTeamId: Optional[str] = None
    secondaryTeamId: Optional[str] = None
    escalationUserId: Optional[str] = None
    slaMinutes: Optional[int] = Field(None, ge=5, le=10080)
    autoEscalateHours: Optional[float] = Field(None, ge=0.5, le=168.0)
    description: Optional[str] = None

class TraceNode(BaseModel):
    id: str
    type: str
    name: str
    details: Dict[str, Any]

class OperationalTraceResponse(BaseModel):
    targetEntity: Dict[str, Any]
    lineageChain: List[TraceNode]
    organization: TraceNode
    region: Optional[TraceNode] = None
    store: Optional[TraceNode] = None
    department: Optional[TraceNode] = None
    primaryTeam: Optional[TraceNode] = None
    escalationOwner: Optional[TraceNode] = None
    ownershipMapping: Optional[Dict[str, Any]] = None
    traceSummary: str

# 3. Feedback Schemas (Phase 3 Multichannel Feedback Ingestion)
class FeedbackCreate(BaseModel):
    storeId: Optional[str] = None
    organizationId: Optional[str] = None
    regionId: Optional[str] = None
    departmentId: Optional[str] = None
    rawText: str = Field(..., min_length=1)
    channelType: Optional[str] = "MANUAL_ENTRY"
    sourceType: Optional[str] = None
    submitterType: Optional[str] = "CUSTOMER"
    privacyClassification: Optional[str] = "INTERNAL"
    languageCode: Optional[str] = "en"
    submittedAt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    allowDuplicates: Optional[bool] = True

class BulkFeedbackCreate(BaseModel):
    items: List[FeedbackCreate]
    rejectDuplicates: Optional[bool] = False

class FeedbackStatusUpdate(BaseModel):
    processingStatus: Optional[str] = Field(None, pattern="^(received|validating|processing|analyzed|failed|reviewed)$")
    status: Optional[str] = Field(None, pattern="^(NEW|TRIAGED|LINKED_TO_INCIDENT|IGNORED|ARCHIVED)$")
    reviewNotes: Optional[str] = None

class FeedbackReviewRequest(BaseModel):
    processingStatus: Optional[str] = Field("reviewed", pattern="^(received|validating|processing|analyzed|failed|reviewed)$")
    status: Optional[str] = Field(None, pattern="^(NEW|TRIAGED|LINKED_TO_INCIDENT|IGNORED|ARCHIVED|IN_REVIEW|RESOLVED)$")
    reviewNotes: Optional[str] = None
    overrides: Optional[Dict[str, Any]] = None

class FollowUpCreate(BaseModel):
    feedbackItemId: str
    turnIndex: int
    question: str
    response: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    organizationId: str
    regionId: Optional[str] = None
    regionName: Optional[str] = None
    storeId: str
    storeName: Optional[str] = None
    departmentId: Optional[str] = None
    departmentName: Optional[str] = None
    sourceType: str
    channelType: Optional[str] = "MANUAL_ENTRY"
    submitterType: Optional[str] = "CUSTOMER"
    privacyClassification: Optional[str] = "INTERNAL"
    processingStatus: Optional[str] = "received"
    status: Optional[str] = "NEW"
    rawText: str
    languageCode: str
    normalizedText: Optional[str] = None
    contentHash: Optional[str] = None
    isDuplicate: bool = False
    duplicateOfId: Optional[str] = None
    aiInterpretation: Optional[Dict[str, Any]] = None
    humanOverrides: Optional[Dict[str, Any]] = None
    effectiveInterpretation: Optional[Dict[str, Any]] = None
    reviewedBy: Optional[str] = None
    reviewedAt: Optional[str] = None
    reviewNotes: Optional[str] = None
    processingError: Optional[str] = None
    sentimentScore: Optional[float] = None
    isAmbiguous: bool = False
    hasPii: bool = False
    metadata: Optional[Dict[str, Any]] = None
    investigationStatus: Optional[str] = "NOT_NEEDED"
    enrichedText: Optional[str] = None
    submittedAt: Optional[str] = None
    createdAt: str
    updatedAt: str
    # Phase 15 Multilingual Intelligence Hardening Fields
    detectedLanguageInfo: Optional[Dict[str, Any]] = None
    normalizedInterpretation: Optional[str] = None
    extractedIssue: Optional[Dict[str, Any]] = None
    multilingualConfidence: Optional[float] = None
    spellingCorrections: Optional[Dict[str, str]] = None

class FeedbackUnderstandingResponse(BaseModel):
    feedbackId: str
    systemFacts: Dict[str, Any]
    aiDerivedFacts: Dict[str, Any]
    humanOverrides: Optional[Dict[str, Any]] = None
    effectiveInterpretation: Dict[str, Any]
    processingStatus: str
    status: str


class BulkFeedbackResponse(BaseModel):
    totalProcessed: int
    succeeded: int
    failed: int
    duplicatesDetected: int
    items: List[FeedbackResponse]
    errors: List[Dict[str, Any]]

# Phase 5: Dynamic Investigation & Follow-up Schemas
class InvestigationQuestionResponse(BaseModel):
    id: str
    feedbackItemId: str
    questionKey: str
    questionText: str
    questionType: str = "text"
    options: Optional[List[str]] = None
    reason: str
    priority: int = 1
    status: str = "PENDING"
    answer: Optional[str] = None
    answeredBy: Optional[str] = None
    answeredAt: Optional[str] = None
    createdAt: str
    updatedAt: str

class QuestionAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)

class AddCustomQuestionRequest(BaseModel):
    questionText: str = Field(..., min_length=3)
    questionKey: Optional[str] = "operator_inquiry"
    questionType: Optional[str] = "text"
    reason: Optional[str] = "Operator inquiry for operational clarification"
    options: Optional[List[str]] = None

class DismissQuestionRequest(BaseModel):
    reason: Optional[str] = None

class InvestigationSummaryResponse(BaseModel):
    feedbackItemId: str
    investigationStatus: str
    missingFields: List[str]
    questions: List[InvestigationQuestionResponse]
    hasEnrichedText: bool = False
    enrichedText: Optional[str] = None

# Phase 6: Cross-Source Semantic Issue Clustering Schemas
class ClusterMemberResponse(BaseModel):
    feedbackItemId: str
    similarityScore: float
    correlationType: str
    rawText: str
    channelType: str
    submitterType: str
    submittedAt: str
    evidenceExcerpt: Optional[str] = None

class ClusterResponse(BaseModel):
    id: str
    organizationId: str
    storeId: Optional[str] = None
    storeName: Optional[str] = None
    title: str
    category: str
    summary: str
    status: str
    confidenceScore: float
    qualityScore: float
    primaryEntity: Optional[str] = None
    primaryLocation: Optional[str] = None
    feedbackCount: int
    sourceDiversityCount: int
    sources: Optional[List[str]] = None
    earliestFeedbackAt: Optional[str] = None
    latestFeedbackAt: Optional[str] = None
    createdAt: str
    updatedAt: str
    members: Optional[List[ClusterMemberResponse]] = None

class ClusterCreateRequest(BaseModel):
    storeId: Optional[str] = None
    timeWindowHours: Optional[int] = 72
    similarityThreshold: Optional[float] = 0.65

class ClusterMergeRequest(BaseModel):
    primaryClusterId: str
    secondaryClusterId: str
    mergedTitle: Optional[str] = None
    justification: Optional[str] = None

class ClusterSplitRequest(BaseModel):
    feedbackItemIdsToEject: List[str] = Field(..., min_length=1)
    newClusterTitle: Optional[str] = None
    justification: Optional[str] = None

class ClusterUpdateRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    primaryLocation: Optional[str] = None
    primaryEntity: Optional[str] = None

# 4. Issue & Clustering Schemas
class IssueCreate(BaseModel):
    storeId: str
    departmentId: Optional[str] = None
    assetId: Optional[str] = None
    title: str
    description: str
    severityScore: float = Field(0.5, ge=0.0, le=1.0)
    urgencyScore: float = Field(0.5, ge=0.0, le=1.0)
    impactScopeScore: float = Field(0.5, ge=0.0, le=1.0)
    assignedTeamId: Optional[str] = None
    feedbackItemIds: Optional[List[str]] = None

class IssueStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(DETECTED|TRIAGED|DISPATCHED|IN_PROGRESS|REMEDIATED|VERIFYING|CLOSED|REOPENED)$")
    justification: Optional[str] = None

class IssuePriorityOverride(BaseModel):
    newPriorityScore: int = Field(..., ge=1, le=100)
    justification: str = Field(..., min_length=5)

class IssueResponse(BaseModel):
    id: str
    organizationId: str
    storeId: str
    departmentId: Optional[str] = None
    assetId: Optional[str] = None
    clusterId: Optional[str] = None
    title: str
    description: str
    status: str
    priorityScore: int
    priorityTier: str
    severityScore: float
    urgencyScore: float
    impactScopeScore: float
    confidenceScore: float
    isEmergingAnomaly: bool
    anomalyVelocityZScore: Optional[float] = 0.0
    assignedTeamId: Optional[str] = None
    assignedTeamName: Optional[str] = None
    assignedUserId: Optional[str] = None
    assignedUserName: Optional[str] = None
    slaMinutes: Optional[int] = 60
    slaDeadline: Optional[str] = None
    routingStatus: Optional[str] = "ROUTED"
    routingDecisionId: Optional[str] = None
    rootCauseHypothesis: Optional[str] = None
    feedbackCount: int
    recurrenceCount: Optional[int] = 0
    geographicSpreadCount: Optional[int] = 1
    factorBreakdown: Optional[Dict[str, Any]] = None
    prioritizationExplanation: Optional[str] = None
    createdAt: str
    updatedAt: str

# Phase 8: Prioritization Schemas
class PriorityCalculationResult(BaseModel):
    priorityScore: int
    priorityTier: str
    factorContributions: Dict[str, float]
    confidenceDiscount: float
    uncertaintyScore: float
    explainableSummary: str
    evidenceMetrics: Dict[str, Any]

class PriorityWeightConfig(BaseModel):
    severityWeight: float = 0.25
    urgencyWeight: float = 0.20
    operationalImpactWeight: float = 0.15
    safetyWeight: float = 0.20
    growthWeight: float = 0.10
    geographicSpreadWeight: float = 0.05
    recurrenceWeight: float = 0.05

# 5. Alert Schemas (Phase 7: Emerging Issue Detection)
class AlertResponse(BaseModel):
    id: str
    organizationId: str
    storeId: str
    issueId: str
    alertType: str
    severity: str
    urgency: Optional[str] = "MEDIUM"
    confidence: Optional[float] = 0.85
    message: str
    what: Optional[str] = None
    whereZone: Optional[str] = None
    observationCount: Optional[int] = 1
    sourcesSummary: Optional[List[str]] = None
    baselineDiff: Optional[float] = 0.0
    velocityZscore: Optional[float] = 0.0
    growthRate: Optional[float] = 0.0
    baselineStatus: Optional[str] = "NORMAL"
    whyGenerated: Optional[str] = None
    uncertainties: Optional[List[str]] = None
    status: Optional[str] = "NEW"
    isAcknowledged: bool = False
    acknowledgedBy: Optional[str] = None
    acknowledgedAt: Optional[str] = None
    escalatedToTeamId: Optional[str] = None
    escalatedBy: Optional[str] = None
    escalatedAt: Optional[str] = None
    dismissedBy: Optional[str] = None
    dismissedAt: Optional[str] = None
    dismissReason: Optional[str] = None
    createdAt: str

class AlertEscalateRequest(BaseModel):
    targetTeamId: str
    notes: Optional[str] = None

class AlertDismissRequest(BaseModel):
    reason: str = Field(..., min_length=3)

class EmergingDetectionRequest(BaseModel):
    storeId: Optional[str] = None
    recentWindowHours: Optional[int] = 24
    baselineWindowDays: Optional[int] = 14
    minEvidenceThreshold: Optional[int] = 2
    zscoreThreshold: Optional[float] = 1.8

# 6. Action Schemas
class ActionApprovalUpdate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    justification: Optional[str] = None

class ActionOverrideUpdate(BaseModel):
    newTargetTeamId: str
    overrideReason: str = Field(..., min_length=5)

class ActionPlanResponse(BaseModel):
    id: str
    organizationId: str
    issueId: str
    recommendedAction: str
    targetTeamId: str
    targetTeamName: Optional[str] = None
    requiresHumanApproval: bool
    approvalStatus: str
    approvedBy: Optional[str] = None
    approvedAt: Optional[str] = None
    overrideReason: Optional[str] = None
    slaDeadline: str
    createdAt: str
    updatedAt: str

# 7. Resolution Schemas
class ResolutionCreate(BaseModel):
    actionPlanId: str
    technicianNotes: str = Field(..., min_length=5)

class ResolutionResponse(BaseModel):
    id: str
    organizationId: str
    issueId: str
    actionPlanId: str
    technicianNotes: str
    resolvedBy: str
    resolvedByName: Optional[str] = None
    resolvedAt: str
    verificationStatus: str
    verificationScorecard: Optional[Dict[str, Any]] = None
    createdAt: str
    updatedAt: str

# 8. Evidence & Lineage Schemas (Phase 9)
class EvidenceResponse(BaseModel):
    id: str
    organizationId: str
    issueId: str
    feedbackItemId: str
    verbatimQuote: str
    sourceMetadata: Dict[str, Any]
    confidenceScore: float
    lineageStage: Optional[str] = "EXTRACTION"
    claimType: Optional[str] = "FACT"
    uncertaintyNote: Optional[str] = None
    createdAt: str

class LineageNode(BaseModel):
    id: str
    type: str  # FEEDBACK, EXTRACTION, INVESTIGATION, CLUSTER, ALERT, PRIORITY, ACTION, RESOLUTION
    label: str
    claimType: str  # FACT, HYPOTHESIS, RECOMMENDATION, UNKNOWN
    confidence: float
    details: Dict[str, Any]

class LineageEdge(BaseModel):
    source: str
    target: str
    relation: str

class LineageGraphResponse(BaseModel):
    rootId: str
    rootType: str
    nodes: List[LineageNode]
    edges: List[LineageEdge]
    factsCount: int
    hypothesesCount: int
    recommendationsCount: int
    unknownsCount: int


# 9. Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: str
    organizationId: str
    userId: Optional[str] = None
    userEmail: Optional[str] = None
    entityType: str
    entityId: str
    action: str
    previousState: Optional[Dict[str, Any]] = None
    newState: Optional[Dict[str, Any]] = None
    justification: Optional[str] = None
    ipAddress: Optional[str] = None
    createdAt: str


# 10. Intelligent Operational Routing Schemas (Phase 10)
class RoutingDecisionResponse(BaseModel):
    id: str
    issueId: str
    organizationId: str
    selectedTeamId: Optional[str] = None
    selectedTeamName: Optional[str] = None
    assignedUserId: Optional[str] = None
    assignedUserName: Optional[str] = None
    routingTier: str
    routingStrategy: str
    reason: str
    supportingData: Optional[Dict[str, Any]] = None
    confidence: float
    isAmbiguous: bool
    fallbackTeamId: Optional[str] = None
    fallbackTeamName: Optional[str] = None
    isHumanOverride: bool = False
    overrideBy: Optional[str] = None
    overrideReason: Optional[str] = None
    slaMinutes: int
    slaDeadline: str
    escalationDeadline: Optional[str] = None
    createdAt: str

class IssueReassignRequest(BaseModel):
    targetTeamId: Optional[str] = None
    targetUserId: Optional[str] = None
    reassignmentReason: str = Field(..., min_length=3)

class IssueEscalateRequest(BaseModel):
    escalationReason: str = Field(..., min_length=3)
    targetTeamId: Optional[str] = None

class RoutingSimulationRequest(BaseModel):
    category: str
    storeId: str
    severity: Optional[float] = 0.5
    urgency: Optional[float] = 0.5
    isSafetyHazard: Optional[bool] = False
    departmentId: Optional[str] = None

class TriageQueueItemResponse(BaseModel):
    issue: IssueResponse
    ambiguityReason: str
    suggestedTeams: List[Dict[str, Any]]
    routedAt: str


# Phase 12: Post-Intervention Outcome Measurement Schemas
class BaselineSnapshot(BaseModel):
    windowStart: str
    windowEnd: str
    windowHours: float
    complaintVolume: int
    issueFrequencyPerDay: float
    avgSeverity: float
    affectedLocationsCount: int
    affectedLocations: List[str]
    responseTimeMinutes: Optional[int] = None
    resolutionTimeMinutes: Optional[int] = None
    slaCompliance: bool = True
    sampleCitations: Optional[List[Dict[str, Any]]] = None

class InterventionInfo(BaseModel):
    timestamp: str
    actionPlanId: Optional[str] = None
    resolutionId: Optional[str] = None
    technicianNotes: Optional[str] = None
    resolvedBy: Optional[str] = None
    resolvedByName: Optional[str] = None
    actionDescription: Optional[str] = None

class ObservationWindow(BaseModel):
    windowStart: str
    windowEnd: str
    windowHours: float
    minObservationHoursRequired: float = 12.0
    isWindowSufficient: bool
    complaintVolume: int
    issueFrequencyPerDay: float
    recurrenceCount: int
    avgSeverity: float
    affectedLocationsCount: int
    affectedLocations: List[str]

class OutcomeComparison(BaseModel):
    complaintVolumeDelta: int
    volumeChangePct: float
    frequencyDeltaPerDay: float
    frequencyChangePct: float
    severityDelta: float
    recurrenceCount: int
    affectedLocationsDelta: int
    responseTimeMinutes: Optional[int] = None
    resolutionTimeMinutes: Optional[int] = None
    slaCompliance: bool = True

class OutcomeEvidenceItem(BaseModel):
    stage: str  # 'BASELINE', 'INTERVENTION', 'POST_OBSERVATION', 'DETERMINATION'
    title: str
    claim: str
    verbatimQuote: Optional[str] = None
    feedbackItemId: Optional[str] = None
    timestamp: Optional[str] = None
    sourceMetadata: Optional[Dict[str, Any]] = None

class OutcomeMeasurementResponse(BaseModel):
    id: str
    organizationId: str
    issueId: str
    issueTitle: str
    storeId: str
    storeName: Optional[str] = None
    resolutionId: Optional[str] = None
    actionPlanId: Optional[str] = None
    intervention: InterventionInfo
    baseline: BaselineSnapshot
    observationWindow: ObservationWindow
    comparison: OutcomeComparison
    outcomeStatus: str  # 'Improved' | 'No significant change' | 'Worsened' | 'Inconclusive'
    statusMessage: Optional[str] = None  # e.g. "outcome cannot yet be determined."
    confidence: float
    evidence: List[OutcomeEvidenceItem]
    measuredAt: str
    createdAt: str
    updatedAt: str

class OutcomeEvaluationRequest(BaseModel):
    observationHours: Optional[float] = None
    minObservationHours: Optional[float] = None
    forceReevaluate: Optional[bool] = False

class OutcomeDashboardSummary(BaseModel):
    totalResolvedIssues: int
    improvedCount: int
    noChangeCount: int
    worsenedCount: int
    inconclusiveCount: int
    improvedRatePct: float
    avgResolutionTimeHours: float
    slaComplianceRatePct: float
    avgImprovementPct: float
    outcomes: List[OutcomeMeasurementResponse]
    categoryBreakdown: Dict[str, Dict[str, int]]


# Phase 14: AI Operational Intelligence Briefs Schemas
class EpistemicClaim(BaseModel):
    id: str
    type: str  # 'OBSERVATION' | 'HYPOTHESIS' | 'RECOMMENDATION' | 'UNKNOWN'
    section: str
    statement: str
    groundingSource: str
    confidence: float
    evidenceIds: Optional[List[str]] = None

class WhatChangedSection(BaseModel):
    summaryText: str
    feedbackVolumeDelta: int
    feedbackVolumeChangePct: float
    newIssuesCount: int
    resolvedIssuesCount: int
    slaComplianceRatePct: float
    slaShiftPct: float
    sentimentShift: float
    operatingStatusChanges: List[Dict[str, Any]]

class EmergingIssueItem(BaseModel):
    alertId: Optional[str] = None
    issueId: Optional[str] = None
    title: str
    alertType: str
    severity: str
    velocityZscore: float
    observationCount: int
    whyGenerated: str
    sourcesSummary: List[str]

class PriorityIssueItem(BaseModel):
    issueId: str
    title: str
    priorityScore: int
    priorityTier: str
    severityScore: float
    urgencyScore: float
    impactScopeScore: float
    isSafetyHazard: bool
    status: str
    assignedTeamName: Optional[str] = None
    slaDeadline: Optional[str] = None
    explainableSummary: str

class AffectedLocationItem(BaseModel):
    storeId: str
    storeName: str
    departmentId: Optional[str] = None
    departmentName: Optional[str] = None
    incidentCount: int
    feedbackCount: int
    riskLevel: str

class BriefEvidenceCitation(BaseModel):
    feedbackItemId: str
    verbatimQuote: str
    sourceType: str
    channelType: str
    timestamp: str
    sentimentScore: Optional[float] = None
    storeName: Optional[str] = None

class BriefHypothesisItem(BaseModel):
    issueId: Optional[str] = None
    hypothesis: str
    supportingObservations: List[str]
    confidence: float
    uncertainties: List[str]

class BriefRecommendationItem(BaseModel):
    actionPlanId: Optional[str] = None
    issueId: str
    recommendation: str
    targetTeamName: str
    urgencyTier: str
    requiresApproval: bool
    groundedRationale: str

class BriefUncertaintyItem(BaseModel):
    area: str
    description: str
    riskOfInaction: str
    missingInformation: str

class BriefUnresolvedIssueItem(BaseModel):
    issueId: str
    title: str
    priorityTier: str
    status: str
    ageHours: float
    assignedTeamName: Optional[str] = None
    slaStatus: str

class BriefInterventionOutcomeItem(BaseModel):
    issueId: str
    issueTitle: str
    outcomeStatus: str  # 'Improved' | 'No significant change' | 'Worsened' | 'Inconclusive'
    statusMessage: str
    frequencyChangePct: float
    recurrenceCount: int
    slaCompliance: bool
    confidence: float

class OperationalBriefResponse(BaseModel):
    id: str
    organizationId: str
    storeId: Optional[str] = None
    storeName: Optional[str] = None
    regionId: Optional[str] = None
    timeframeType: str  # 'DAILY' | 'WEEKLY' | 'CUSTOM'
    startDate: str
    endDate: str
    title: str
    executiveSummary: str
    whatChanged: WhatChangedSection
    emergingIssues: List[EmergingIssueItem]
    highestPriorityIssues: List[PriorityIssueItem]
    affectedLocations: List[AffectedLocationItem]
    evidence: List[BriefEvidenceCitation]
    hypotheses: List[BriefHypothesisItem]
    recommendedActions: List[BriefRecommendationItem]
    uncertainties: List[BriefUncertaintyItem]
    unresolvedIssues: List[BriefUnresolvedIssueItem]
    interventionOutcomes: List[BriefInterventionOutcomeItem]
    labeledClaims: List[EpistemicClaim]
    deterministicMetrics: Dict[str, Any]
    generatedBy: Optional[str] = None
    createdAt: str
    updatedAt: str

class BriefGenerateRequest(BaseModel):
    timeframeType: Optional[str] = "DAILY"  # DAILY | WEEKLY | CUSTOM
    storeId: Optional[str] = None
    regionId: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None


# -----------------------------------------------------------------------------
# Phase 15: Multilingual Operational Intelligence Hardening Schemas
# -----------------------------------------------------------------------------
class MultilingualParseRequest(BaseModel):
    text: str = Field(..., min_length=1)
    languageHint: Optional[str] = None

class MultilingualDetectedLanguage(BaseModel):
    code: str
    name: str
    script: str
    isTransliterated: bool = False
    isCodeMixed: bool = False
    confidence: float
    evidence: List[str] = []

class MultilingualExtractedIssue(BaseModel):
    category: str
    issueType: str
    severity: str
    urgency: str
    isSafetyHazard: bool
    affectedEntity: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None

class MultilingualParseResponse(BaseModel):
    rawText: str
    detectedLanguage: MultilingualDetectedLanguage
    normalizedInterpretation: str
    extractedIssue: MultilingualExtractedIssue
    confidence: float
    spellingCorrections: Optional[Dict[str, str]] = None
    evidence: Optional[List[Dict[str, Any]]] = None

class MultilingualBenchmarkResponse(BaseModel):
    totalTestCases: int
    languagesCovered: List[str]
    detectionAccuracyPct: float
    categoryAccuracyPct: float
    issueTypeAccuracyPct: float
    safetyHazardAccuracyPct: float
    crossLingualClusteringPrecisionPct: float
    evaluationDatasetSize: int
    testCaseResults: List[Dict[str, Any]]



