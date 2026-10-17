/**
 * R5 Operational Intelligence Platform
 * Shared Domain Types
 * 
 * Strict typing for Enterprise Physical Operations:
 * Organization -> Region -> Store -> Department -> Team -> Feedback -> Issue -> Alert -> Action -> Resolution -> Evidence
 * Plus future segregated Personal/Home appliance schema.
 */

// 1. Core Organizational Hierarchy
export interface Organization {
  id: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
}

export interface Region {
  id: string;
  organizationId: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
}

export interface Store {
  id: string;
  organizationId: string;
  regionId: string;
  name: string;
  storeNumber: number;
  address: {
    street: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
  };
  timezone: string;
  createdAt: string;
  updatedAt: string;
}

export interface Department {
  id: string;
  organizationId: string;
  storeId: string;
  name: string; // e.g. 'Dairy', 'Produce', 'Checkout', 'HVAC'
  floorZone?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Asset {
  id: string;
  organizationId: string;
  storeId: string;
  departmentId?: string;
  name: string;
  assetTag: string;
  category: 'REFRIGERATION' | 'POS_TERMINAL' | 'HVAC' | 'RESTROOM' | 'LIGHTING' | 'STORAGE' | 'OTHER';
  status: 'OPERATIONAL' | 'DEGRADED' | 'OUT_OF_SERVICE';
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

// 2. Teams & Users
export type TeamType = 
  | 'FACILITIES'
  | 'HVAC_REFRIGERATION'
  | 'JANITORIAL'
  | 'IT_POS'
  | 'MERCHANDISING'
  | 'LOSS_PREVENTION'
  | 'STORE_OPERATIONS';

export interface OperationalTeam {
  id: string;
  organizationId: string;
  storeId?: string | null; // null if regional or centralized vendor
  name: string;
  teamType: TeamType;
  slaTier: 'STANDARD' | 'EXPEDITED' | 'MISSION_CRITICAL';
  contactEmail?: string;
  createdAt: string;
  updatedAt: string;
}

export type RoleName =
  | 'ORGANIZATION_ADMIN'
  | 'OPERATIONS_MANAGER'
  | 'REGIONAL_MANAGER'
  | 'STORE_MANAGER'
  | 'MAINTENANCE_TEAM'
  | 'ANALYST'
  | 'VIEWER';

export interface User {
  id: string;
  organizationId: string;
  email: string;
  fullName: string;
  role: RoleName;
  storeId?: string | null; // Store-level restriction if applicable
  regionId?: string | null; // Region-level restriction if applicable
  teamId?: string | null; // Assigned operational team if applicable
  isActive: boolean;
  lastLoginAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

// 3. Feedback Ingestion
export type FeedbackSourceType = 
  | 'QR_KIOSK'
  | 'ASSOCIATE_APP'
  | 'POS_EXCEPTION'
  | 'CUSTOMER_VOICE'
  | 'WEB_FORM';

export interface FeedbackItem {
  id: string;
  organizationId: string;
  storeId: string;
  departmentId?: string | null;
  sourceType: FeedbackSourceType;
  rawText: string;
  languageCode: string;
  normalizedText?: string;
  detectedLanguageInfo?: Record<string, unknown>;
  normalizedInterpretation?: string;
  extractedIssue?: Record<string, unknown>;
  multilingualConfidence?: number;
  sentimentScore?: number; // -1.0 to 1.0
  isAmbiguous: boolean;
  hasPii: boolean;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface FollowUpExchange {
  id: string;
  feedbackItemId: string;
  turnIndex: number;
  question: string;
  response?: string;
  createdAt: string;
}

// 4. Issues & Emerging Incidents
export type IssueStatus =
  | 'DETECTED'
  | 'TRIAGED'
  | 'DISPATCHED'
  | 'IN_PROGRESS'
  | 'REMEDIATED'
  | 'VERIFYING'
  | 'CLOSED'
  | 'REOPENED';

export type PriorityTier = 'P1_CRITICAL' | 'P2_HIGH' | 'P3_MEDIUM' | 'P4_LOW';

export interface Issue {
  id: string;
  organizationId: string;
  storeId: string;
  departmentId?: string | null;
  assetId?: string | null;
  title: string;
  description: string;
  status: IssueStatus;
  priorityScore: number; // 1 to 100
  priorityTier: PriorityTier;
  severityScore: number; // 0.0 to 1.0
  urgencyScore: number; // 0.0 to 1.0
  impactScopeScore: number; // 0.0 to 1.0
  confidenceScore: number; // 0.0 to 1.0
  isEmergingAnomaly: boolean;
  anomalyVelocityZScore?: number;
  assignedTeamId?: string | null;
  rootCauseHypothesis?: string;
  feedbackCount: number;
  createdAt: string;
  updatedAt: string;
}

// 5. Alerts
export type AlertType = 
  | 'EMERGING_ANOMALY'
  | 'SLA_WARNING'
  | 'SLA_BREACH'
  | 'SAFETY_HAZARD'
  | 'RECURRENCE_DETECTED';

export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL';

export interface Alert {
  id: string;
  organizationId: string;
  storeId: string;
  issueId: string;
  alertType: AlertType;
  severity: AlertSeverity;
  message: string;
  isAcknowledged: boolean;
  acknowledgedBy?: string | null;
  acknowledgedAt?: string | null;
  createdAt: string;
}

// 6. Actions & Approvals
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'OVERRIDDEN' | 'REJECTED';

export interface ActionPlan {
  id: string;
  organizationId: string;
  issueId: string;
  recommendedAction: string;
  targetTeamId: string;
  requiresHumanApproval: boolean;
  approvalStatus: ApprovalStatus;
  approvedBy?: string | null;
  approvedAt?: string | null;
  overrideReason?: string | null;
  slaDeadline: string;
  createdAt: string;
  updatedAt: string;
}

// 7. Resolutions & Verification
export type VerificationStatus = 
  | 'PENDING_VERIFICATION'
  | 'VERIFIED_RESOLVED'
  | 'RECURRENCE_DETECTED'
  | 'UNVERIFIED';

export interface Resolution {
  id: string;
  organizationId: string;
  issueId: string;
  actionPlanId: string;
  technicianNotes: string;
  resolvedBy: string;
  resolvedAt: string;
  verificationStatus: VerificationStatus;
  verificationScorecard?: {
    preFeedbackRate: number;
    postFeedbackRate: number;
    feedbackRateDeltaPct: number;
    sentimentShift: number;
    recurrenceCount: number;
    evaluatedAt: string;
  };
  createdAt: string;
  updatedAt: string;
}

// 8. Evidence Item
export interface Evidence {
  id: string;
  organizationId: string;
  issueId: string;
  feedbackItemId: string;
  verbatimQuote: string;
  sourceMetadata: {
    sourceType: FeedbackSourceType;
    language: string;
    submittedAt: string;
    storeName?: string;
    departmentName?: string;
  };
  confidenceScore: number;
  createdAt: string;
}

// 9. Audit Logging
export interface AuditLog {
  id: string;
  organizationId: string;
  userId?: string | null;
  entityType: string; // 'ISSUE' | 'ACTION' | 'FEEDBACK' | 'USER' | 'TEAM'
  entityId: string;
  action: string; // 'STATUS_CHANGE' | 'APPROVAL' | 'OVERRIDE' | 'ROUTING_REASSIGN'
  previousState?: Record<string, unknown> | null;
  newState?: Record<string, unknown> | null;
  justification?: string | null;
  ipAddress?: string | null;
  userAgent?: string | null;
  createdAt: string;
}

// 10. Future Extensibility: Personal / Home Mode (Completely Segregated)
export type PersonalApplianceType = 'TV' | 'REFRIGERATOR' | 'WASHING_MACHINE' | 'AC';

export interface PersonalAppliance {
  id: string;
  userId: string;
  applianceType: PersonalApplianceType;
  brand: string;
  modelNumber?: string;
  serialNumber?: string;
  purchaseDate?: string;
  warrantyUntil?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PersonalServiceTicket {
  id: string;
  applianceId: string;
  userId: string;
  complaintDescription: string;
  classifiedCategory: string;
  routedServiceChannel: string;
  status: 'SUBMITTED' | 'IN_REVIEW' | 'CHANNEL_NOTIFIED' | 'RESOLVED';
  externalReferenceId?: string;
  createdAt: string;
  updatedAt: string;
}

// 11. Phase 12: Post-Intervention Outcome Measurement
export type OutcomeStatus = 'Improved' | 'No significant change' | 'Worsened' | 'Inconclusive';

export interface BaselineSnapshot {
  windowStart: string;
  windowEnd: string;
  windowHours: number;
  complaintVolume: number;
  issueFrequencyPerDay: number;
  avgSeverity: number;
  affectedLocationsCount: number;
  affectedLocations: string[];
  responseTimeMinutes?: number;
  resolutionTimeMinutes?: number;
  slaCompliance: boolean;
  sampleCitations?: Array<Record<string, unknown>>;
}

export interface ObservationWindow {
  windowStart: string;
  windowEnd: string;
  windowHours: number;
  minObservationHoursRequired: number;
  isWindowSufficient: boolean;
  complaintVolume: number;
  issueFrequencyPerDay: number;
  recurrenceCount: number;
  avgSeverity: number;
  affectedLocationsCount: number;
  affectedLocations: string[];
}

export interface OutcomeComparison {
  complaintVolumeDelta: number;
  volumeChangePct: number;
  frequencyDeltaPerDay: number;
  frequencyChangePct: number;
  severityDelta: number;
  recurrenceCount: number;
  affectedLocationsDelta: number;
  responseTimeMinutes?: number;
  resolutionTimeMinutes?: number;
  slaCompliance: boolean;
}

export interface OutcomeEvidenceItem {
  stage: 'BASELINE' | 'INTERVENTION' | 'POST_OBSERVATION' | 'DETERMINATION';
  title: string;
  claim: string;
  verbatimQuote?: string;
  feedbackItemId?: string;
  timestamp?: string;
  sourceMetadata?: Record<string, unknown>;
}

export interface OutcomeMeasurement {
  id: string;
  organizationId: string;
  issueId: string;
  issueTitle: string;
  storeId: string;
  storeName?: string;
  resolutionId?: string;
  actionPlanId?: string;
  intervention: {
    timestamp: string;
    actionPlanId?: string;
    resolutionId?: string;
    technicianNotes?: string;
    resolvedBy?: string;
    resolvedByName?: string;
    actionDescription?: string;
  };
  baseline: BaselineSnapshot;
  observationWindow: ObservationWindow;
  comparison: OutcomeComparison;
  outcomeStatus: OutcomeStatus;
  statusMessage?: string;
  confidence: number;
  evidence: OutcomeEvidenceItem[];
  measuredAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface OutcomeDashboardSummary {
  totalResolvedIssues: number;
  improvedCount: number;
  noChangeCount: number;
  worsenedCount: number;
  inconclusiveCount: number;
  improvedRatePct: number;
  avgResolutionTimeHours: number;
  slaComplianceRatePct: number;
  avgImprovementPct: number;
  outcomes: OutcomeMeasurement[];
  categoryBreakdown: Record<string, Record<string, number>>;
}

// 12. Phase 14: AI Operational Intelligence Briefs
export type EpistemicClaimType = 'OBSERVATION' | 'HYPOTHESIS' | 'RECOMMENDATION' | 'UNKNOWN';

export interface EpistemicClaim {
  id: string;
  type: EpistemicClaimType;
  section: string;
  statement: string;
  groundingSource: string;
  confidence: number;
  evidenceIds?: string[];
}

export interface WhatChangedSection {
  summaryText: string;
  feedbackVolumeDelta: number;
  feedbackVolumeChangePct: number;
  newIssuesCount: number;
  resolvedIssuesCount: number;
  slaComplianceRatePct: number;
  slaShiftPct: number;
  sentimentShift: number;
  operatingStatusChanges: Array<Record<string, unknown>>;
}

export interface EmergingIssueItem {
  alertId?: string;
  issueId?: string;
  title: string;
  alertType: string;
  severity: string;
  velocityZscore: number;
  observationCount: number;
  whyGenerated: string;
  sourcesSummary: string[];
}

export interface PriorityIssueItem {
  issueId: string;
  title: string;
  priorityScore: number;
  priorityTier: string;
  severityScore: number;
  urgencyScore: number;
  impactScopeScore: number;
  isSafetyHazard: boolean;
  status: string;
  assignedTeamName?: string;
  slaDeadline?: string;
  explainableSummary: string;
}

export interface AffectedLocationItem {
  storeId: string;
  storeName: string;
  departmentId?: string;
  departmentName?: string;
  incidentCount: number;
  feedbackCount: number;
  riskLevel: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'STABLE';
}

export interface BriefEvidenceCitation {
  feedbackItemId: string;
  verbatimQuote: string;
  sourceType: string;
  channelType: string;
  timestamp: string;
  sentimentScore?: number;
  storeName?: string;
}

export interface BriefHypothesisItem {
  issueId?: string;
  hypothesis: string;
  supportingObservations: string[];
  confidence: number;
  uncertainties: string[];
}

export interface BriefRecommendationItem {
  actionPlanId?: string;
  issueId: string;
  recommendation: string;
  targetTeamName: string;
  urgencyTier: string;
  requiresApproval: boolean;
  groundedRationale: string;
}

export interface BriefUncertaintyItem {
  area: string;
  description: string;
  riskOfInaction: string;
  missingInformation: string;
}

export interface BriefUnresolvedIssueItem {
  issueId: string;
  title: string;
  priorityTier: string;
  status: string;
  ageHours: number;
  assignedTeamName?: string;
  slaStatus: string;
}

export interface BriefInterventionOutcomeItem {
  issueId: string;
  issueTitle: string;
  outcomeStatus: OutcomeStatus;
  statusMessage: string;
  frequencyChangePct: number;
  recurrenceCount: number;
  slaCompliance: boolean;
  confidence: number;
}

export interface OperationalBrief {
  id: string;
  organizationId: string;
  storeId?: string;
  storeName?: string;
  regionId?: string;
  timeframeType: 'DAILY' | 'WEEKLY' | 'CUSTOM';
  startDate: string;
  endDate: string;
  title: string;
  executiveSummary: string;
  whatChanged: WhatChangedSection;
  emergingIssues: EmergingIssueItem[];
  highestPriorityIssues: PriorityIssueItem[];
  affectedLocations: AffectedLocationItem[];
  evidence: BriefEvidenceCitation[];
  hypotheses: BriefHypothesisItem[];
  recommendedActions: BriefRecommendationItem[];
  uncertainties: BriefUncertaintyItem[];
  unresolvedIssues: BriefUnresolvedIssueItem[];
  interventionOutcomes: BriefInterventionOutcomeItem[];
  labeledClaims: EpistemicClaim[];
  deterministicMetrics: Record<string, unknown>;
  generatedBy?: string;
  createdAt: string;
  updatedAt: string;
}

// 12. Multilingual Operational Intelligence (Phase 15)
export interface MultilingualDetectedLanguage {
  code: string;
  name: string;
  script: string;
  isTransliterated: boolean;
  isCodeMixed: boolean;
  confidence: number;
  evidence: string[];
}

export interface MultilingualExtractedIssue {
  category: string;
  issueType: string;
  severity: string;
  urgency: string;
  isSafetyHazard: boolean;
  affectedEntity?: string;
  location?: string;
  summary?: string;
}

export interface MultilingualParseResponse {
  rawText: string;
  detectedLanguage: MultilingualDetectedLanguage;
  normalizedInterpretation: string;
  extractedIssue: MultilingualExtractedIssue;
  confidence: number;
  spellingCorrections?: Record<string, string>;
  evidence?: Array<{ source: string; text: string; offsets: [number, number] }>;
}

export interface MultilingualBenchmarkResponse {
  totalTestCases: number;
  languagesCovered: string[];
  detectionAccuracyPct: number;
  categoryAccuracyPct: number;
  issueTypeAccuracyPct: number;
  safetyHazardAccuracyPct: number;
  crossLingualClusteringPrecisionPct: number;
  evaluationDatasetSize: number;
  testCaseResults: Array<Record<string, unknown>>;
}


