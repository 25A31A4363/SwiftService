/**
 * R5 Operational Intelligence Platform - Client-Side Mock Backend Engine
 * Provides 100% autonomous in-browser execution when running on static hosting (e.g., Netlify).
 * Ensures zero 404s and full closed-loop feature demonstration.
 */

const STORAGE_KEY = 'r5_mock_database_v1';

function createInitialDatabase() {
  const now = new Date().toISOString();
  const pastHour = new Date(Date.now() - 3600000).toISOString();
  const pastDay = new Date(Date.now() - 86400000).toISOString();

  return {
    users: [
      { id: 'usr-store', email: 'storemanager@apex.com', fullName: 'David Miller', role: 'STORE_MANAGER', storeId: 'store-104', regionId: 'reg-pnw-01', organizationId: 'org-apex-01', isActive: true },
      { id: 'usr-admin', email: 'orgadmin@apex.com', fullName: 'Eleanor Vance', role: 'ORGANIZATION_ADMIN', storeId: null, regionId: null, organizationId: 'org-apex-01', isActive: true },
      { id: 'usr-ops', email: 'opsmanager@apex.com', fullName: 'Marcus Sterling', role: 'OPERATIONS_MANAGER', storeId: null, regionId: null, organizationId: 'org-apex-01', isActive: true },
      { id: 'usr-reg', email: 'regmanager@apex.com', fullName: 'Sarah Chen', role: 'REGIONAL_MANAGER', storeId: null, regionId: 'reg-pnw-01', organizationId: 'org-apex-01', isActive: true },
      { id: 'usr-maint', email: 'maintenance@apex.com', fullName: 'Carlos Gomez', role: 'MAINTENANCE_TEAM', storeId: 'store-104', regionId: 'reg-pnw-01', organizationId: 'org-apex-01', isActive: true },
      { id: 'usr-analyst', email: 'analyst@apex.com', fullName: 'Priya Sharma', role: 'ANALYST', storeId: null, regionId: null, organizationId: 'org-apex-01', isActive: true },
      { id: 'usr-viewer', email: 'viewer@apex.com', fullName: 'Alex Reed', role: 'VIEWER', storeId: 'store-104', regionId: 'reg-pnw-01', organizationId: 'org-apex-01', isActive: true }
    ],
    organizations: [
      { id: 'org-apex-01', name: 'Apex Retail International', code: 'APEX', description: 'Global omnichannel retail enterprise operating multi-tier physical supercenters and urban metro locations.', status: 'ACTIVE' }
    ],
    regions: [
      { id: 'reg-pnw-01', organizationId: 'org-apex-01', name: 'Pacific Northwest Region', code: 'REG-PNW', description: 'Northwestern regional network consisting of large-format supercenters and fulfillment hubs.' },
      { id: 'reg-na-01', organizationId: 'org-apex-01', name: 'North Atlantic Region', code: 'REG-NA', description: 'Northeastern metropolitan territory encompassing high-density urban express stores.' }
    ],
    stores: [
      { id: 'store-104', organizationId: 'org-apex-01', regionId: 'reg-pnw-01', name: 'Apex Supercenter - Seattle Downtown', storeNumber: 104, city: 'Seattle', state: 'WA', operatingStatus: 'OPERATIONAL' },
      { id: 'store-205', organizationId: 'org-apex-01', regionId: 'reg-na-01', name: 'Apex Metro - Cambridge Galleria', storeNumber: 205, city: 'Cambridge', state: 'MA', operatingStatus: 'MAINTENANCE_HOLD' }
    ],
    departments: [
      { id: 'dept-104-dairy', storeId: 'store-104', name: 'Dairy & Refrigerated', floorZone: 'Aisle 4-5 Perimeter' },
      { id: 'dept-104-pos', storeId: 'store-104', name: 'Front Checkout & Self-Pay', floorZone: 'Front Zone Lanes 1-12' },
      { id: 'dept-104-produce', storeId: 'store-104', name: 'Fresh Produce', floorZone: 'Perimeter West' }
    ],
    assets: [
      { id: 'asset-cooler-4b', storeId: 'store-104', departmentId: 'dept-104-dairy', name: 'Commercial Reach-in Dairy Cooler 4B', assetTag: 'AST-104-CLR-04B', status: 'OPERATIONAL' }
    ],
    teams: [
      { id: 'team-hvac-pnw', organizationId: 'org-apex-01', storeId: 'store-104', regionId: 'reg-pnw-01', name: 'Regional Commercial HVAC & Refrigeration', teamType: 'FACILITIES', specialization: 'REFRIGERATION_HVAC', slaTier: 'EMERGENCY', status: 'ACTIVE' },
      { id: 'team-jan-104', organizationId: 'org-apex-01', storeId: 'store-104', regionId: 'reg-pnw-01', name: 'Store 104 Janitorial & Sanitation', teamType: 'JANITORIAL', specialization: 'JANITORIAL_SANITATION', slaTier: 'HIGH', status: 'ACTIVE' },
      { id: 'team-it-na', organizationId: 'org-apex-01', storeId: null, regionId: 'reg-na-01', name: 'Regional IT & POS Systems', teamType: 'IT_SYSTEMS', specialization: 'POS_HARDWARE', slaTier: 'STANDARD', status: 'ACTIVE' },
      { id: 'team-qa-food', organizationId: 'org-apex-01', storeId: null, regionId: null, name: 'Corporate Food Safety & HACCP', teamType: 'SAFETY_COMPLIANCE', specialization: 'FOOD_SAFETY', slaTier: 'CRITICAL', status: 'ACTIVE' }
    ],
    feedback: [
      {
        id: 'fb-demo-001',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        channelType: 'MOBILE_APP',
        submitterType: 'CUSTOMER',
        languageCode: 'en',
        rawText: 'Water is pooling under the dairy cooler in aisle 4, someone is going to slip and fall!',
        sentimentScore: -0.85,
        processingStatus: 'ANALYZED',
        submittedAt: pastHour,
        aiInterpretation: {
          language: { code: 'en', confidence: 0.99 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.94 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.96 },
          safetyRelevance: { value: 'CRITICAL_HAZARD', isSafetyHazard: true, confidence: 0.95 },
          location: { value: 'Aisle 4', confidence: 0.95 },
          affectedEntity: { value: 'Dairy Cooler', confidence: 0.95 },
          overallConfidence: 0.95
        }
      },
      {
        id: 'fb-demo-002',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        channelType: 'KIOSK',
        submitterType: 'CUSTOMER',
        languageCode: 'es',
        rawText: 'Hay un charco de agua saliendo de la nevera de lacteos en el pasillo cuatro, piso muy resbaloso!',
        sentimentScore: -0.90,
        processingStatus: 'ANALYZED',
        submittedAt: pastHour,
        aiInterpretation: {
          language: { code: 'es', confidence: 0.98 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.92 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.95 },
          safetyRelevance: { value: 'CRITICAL_HAZARD', isSafetyHazard: true, confidence: 0.94 },
          location: { value: 'Pasillo 4', confidence: 0.90 },
          affectedEntity: { value: 'Nevera de Lacteos', confidence: 0.92 },
          overallConfidence: 0.93
        }
      },
      {
        id: 'fb-demo-003',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        channelType: 'SMS',
        submitterType: 'CUSTOMER',
        languageCode: 'fr',
        rawText: "Fuite d'eau importante sous les refrigerateurs de produits laitiers allee 4, sol tres glissant.",
        sentimentScore: -0.88,
        processingStatus: 'ANALYZED',
        submittedAt: pastHour,
        aiInterpretation: {
          language: { code: 'fr', confidence: 0.98 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.93 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.94 },
          safetyRelevance: { value: 'CRITICAL_HAZARD', isSafetyHazard: true, confidence: 0.95 },
          location: { value: 'Allee 4', confidence: 0.92 },
          affectedEntity: { value: 'Refrigerateurs', confidence: 0.94 },
          overallConfidence: 0.94
        }
      },
      {
        id: 'fb-demo-004',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        channelType: 'QR_CODE',
        submitterType: 'CUSTOMER',
        languageCode: 'hi',
        rawText: 'Aisle 4 mein dairy freezer ke paas bohot paani gir raha hai, slip hone ka risk hai.',
        sentimentScore: -0.82,
        processingStatus: 'ANALYZED',
        submittedAt: pastHour,
        aiInterpretation: {
          language: { code: 'hi', confidence: 0.95 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.91 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.93 },
          safetyRelevance: { value: 'CRITICAL_HAZARD', isSafetyHazard: true, confidence: 0.92 },
          location: { value: 'Aisle 4', confidence: 0.90 },
          affectedEntity: { value: 'Dairy Freezer', confidence: 0.91 },
          overallConfidence: 0.92
        }
      },
      {
        id: 'fb-demo-005',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        channelType: 'INTERNAL_APP',
        submitterType: 'EMPLOYEE',
        languageCode: 'en',
        rawText: 'Walk-in cooler 104-B humming loudly, puddle forming on the concrete floor.',
        sentimentScore: -0.75,
        processingStatus: 'ANALYZED',
        submittedAt: pastHour,
        aiInterpretation: {
          language: { code: 'en', confidence: 0.99 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.96 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.97 },
          safetyRelevance: { value: 'POTENTIAL_HAZARD', isSafetyHazard: true, confidence: 0.90 },
          location: { value: 'Dairy Walk-in', confidence: 0.92 },
          affectedEntity: { value: 'Cooler 104-B', confidence: 0.95 },
          overallConfidence: 0.95
        }
      },
      {
        id: 'fb-demo-006',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        channelType: 'VOICE_TRANSCRIPT',
        submitterType: 'CUSTOMER',
        languageCode: 'de',
        rawText: 'Wasseraustritt beim Kuehlregal in Gang 4, Rutschgefahr fuer Kunden!',
        sentimentScore: -0.92,
        processingStatus: 'ANALYZED',
        submittedAt: pastHour,
        aiInterpretation: {
          language: { code: 'de', confidence: 0.98 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.94 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.95 },
          safetyRelevance: { value: 'CRITICAL_HAZARD', isSafetyHazard: true, confidence: 0.96 },
          location: { value: 'Gang 4', confidence: 0.92 },
          affectedEntity: { value: 'Kuehlregal', confidence: 0.94 },
          overallConfidence: 0.95
        }
      }
    ],
    clusters: [
      {
        id: 'cl-demo-cooler-104',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        title: 'Commercial Cooler Refrigerant Leak & Slip Hazard - Dairy Aisle 4',
        category: 'FACILITIES_MAINTENANCE',
        summary: 'Synthesizes 6 empirical reports across Mobile App, Kiosk, SMS, QR Code, and Frontline Voice. 100% grounded in verified customer complaints with high semantic convergence (similarity 0.96).',
        confidenceScore: 0.96,
        qualityScore: 0.95,
        primaryEntity: 'Dairy Reach-in Cooler 4B',
        primaryLocation: 'Aisle 4 Perimeter',
        earliestFeedbackAt: pastHour,
        latestFeedbackAt: now,
        feedbackCount: 6,
        sourceDiversityCount: 5,
        status: 'ACTIVE'
      }
    ],
    alerts: [
      {
        id: 'alt-demo-cooler-104',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        issueId: 'iss-demo-cooler-104',
        alertType: 'EMERGING_ANOMALY',
        severity: 'CRITICAL',
        urgency: 'IMMEDIATE',
        confidence: 0.94,
        what: 'Emerging Refrigeration Failure & Liquid Slip Spike',
        whereZone: 'Apex Supercenter - Seattle Downtown (Store 104)',
        message: 'Sudden burst of 6 complaints in 90 minutes exceeds 14-day historical baseline expectation of 0.03/day (+8.49z velocity). Confirmed across 5 distinct channels.',
        observationCount: 6,
        velocityZscore: 8.49,
        growthRate: 11.0,
        baselineDiff: 5.97,
        baselineStatus: 'ANOMALY',
        whyGenerated: 'Recent frequency (6 reports in 24h) exceeds baseline expectation of 0.03 (Z-Score: +8.49z, Growth: +1100%). Multi-lingual convergence in English, Spanish, French, Hinglish, German.',
        status: 'NEW',
        isAcknowledged: false,
        createdAt: pastHour
      }
    ],
    issues: [
      {
        id: 'iss-demo-cooler-104',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        departmentId: 'dept-104-dairy',
        assetId: 'asset-cooler-4b',
        clusterId: 'cl-demo-cooler-104',
        title: 'Commercial Cooler 4B Defrost Relay Failure & Slip Hazard',
        description: 'Multi-lingual customer and staff alerts reporting water overflow and slip hazard in Aisle 4. Poisson velocity anomaly +8.49z above baseline.',
        status: 'IN_PROGRESS',
        priorityScore: 85,
        priorityTier: 'P1_CRITICAL',
        severityScore: 0.90,
        urgencyScore: 0.95,
        impactScopeScore: 0.75,
        confidenceScore: 0.94,
        isEmergingAnomaly: 1,
        anomalyVelocityZscore: 8.49,
        assignedTeamId: 'team-hvac-pnw',
        assignedTeamName: 'Regional Commercial HVAC & Refrigeration',
        feedbackCount: 6,
        slaMinutes: 30,
        slaDeadline: new Date(Date.now() + 1800000).toISOString(),
        routingStatus: 'ROUTED',
        factorBreakdown: { severity: 22.5, urgency: 19.0, operational_impact: 11.25, safety: 20.0, growth: 10.0, geographic_spread: 2.0, recurrence: 0.0 },
        prioritizationExplanation: 'P1 Critical: Confirmed active liquid slip hazard combined with commercial cold-chain failure triggering mandatory direct safety floor.',
        createdAt: pastHour,
        updatedAt: now
      }
    ],
    actions: [
      {
        id: 'act-demo-cooler-104',
        issueId: 'iss-demo-cooler-104',
        organizationId: 'org-apex-01',
        title: 'Emergency Defrost Repair & Floor Desiccation Dispatch',
        description: 'Authorize emergency on-site dispatch of Senior HVAC Technician Carlos Gomez and Janitorial wet-vac crew.',
        assignedTeamId: 'team-hvac-pnw',
        slaTargetMinutes: 30,
        approvalStatus: 'APPROVED',
        approvedBy: 'usr-store',
        approvedByName: 'David Miller (Store 104 Lead)',
        status: 'IN_PROGRESS',
        createdAt: pastHour
      }
    ],
    resolutions: [
      {
        id: 'res-demo-cooler-104',
        issueId: 'iss-demo-cooler-104',
        actionPlanId: 'act-demo-cooler-104',
        performedByUserId: 'usr-maint',
        performedByUserName: 'Carlos Gomez (Senior HVAC Tech)',
        workSummary: 'Replaced stuck defrost thermostat relay (Part #TR-4402). Evaporator pan drained. Tile floor thoroughly dried with air mover. Verified cabinet temperature at 36.0°F.',
        partsReplaced: 'Defrost Relay Kit TR-4402',
        rootCauseConfirmed: 'Stuck relay contact forced indefinite defrost heating cycle, creating excessive meltwater overflow onto sales floor.',
        cabinetTemperatureF: 36.0,
        spoilageLossAmount: 0.0,
        status: 'VERIFIED',
        createdAt: now
      }
    ],
    outcomes: [
      {
        id: 'out-demo-cooler-104',
        issueId: 'iss-demo-cooler-104',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        outcomeStatus: 'Substantially Improved',
        baselineComplaintRatePerDay: 56.47,
        postInterventionComplaintRatePerDay: 0.0,
        frequencyDeltaPercent: -100.0,
        recurrenceCount: 0,
        observationHoursCompleted: 24.0,
        isDefinitive: true,
        explanation: 'Post-intervention telemetry confirms 100% reduction in customer complaints following thermostat relay replacement. IoT sensor telemetry verified at 36.2°F stable.',
        evaluatedAt: now
      }
    ],
    briefs: [
      {
        id: 'brief-demo-001',
        organizationId: 'org-apex-01',
        storeId: 'store-104',
        title: 'AI Operational Intelligence Brief - Apex Supercenter - Seattle Downtown',
        timeframeType: 'DAILY',
        executiveSummary: 'Daily operations report for Store 104. Critical P1 cold-chain failure in Dairy Aisle 4 was mitigated within 30m SLA window. Senior technician Carlos Gomez replaced stuck relay with $0 inventory spoilage. Post-intervention audit confirms 100% complaint reduction.',
        confidenceScore: 0.98,
        groundedClaimCount: 35,
        recommendations: [
          { priority: 'HIGH', text: 'Schedule 30-day preventative maintenance cycle on CoolTech-400 compressors.', owner: 'team-hvac-pnw' },
          { priority: 'MEDIUM', text: 'Inspect moisture barrier tiles in Aisle 4 perimeter.', owner: 'team-jan-104' },
          { priority: 'LOW', text: 'Calibrate digital temperature logging sensors.', owner: 'team-qa-food' }
        ],
        createdAt: now
      }
    ],
    investigations: {
      'fb-demo-005': {
        feedbackItemId: 'fb-demo-005',
        investigationStatus: 'SUFFICIENT',
        missingFields: [],
        questions: [
          {
            id: 'invq-001',
            feedbackItemId: 'fb-demo-005',
            questionKey: 'clarify_location',
            questionText: 'Which specific reach-in or walk-in unit is humming and leaking?',
            questionType: 'choice',
            options: ['Dairy Walk-in 104-B', 'Beverage Cooler 2A', 'Frozen Meat 6C', 'Other'],
            reason: 'Pinpoints the exact physical asset for technician dispatch.',
            status: 'ANSWERED',
            answer: 'Dairy Walk-in 104-B'
          }
        ]
      }
    }
  };
}

class MockBackend {
  constructor() {
    this.db = this.loadDatabase();
  }

  loadDatabase() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // ignore
    }
    const fresh = createInitialDatabase();
    this.saveDatabase(fresh);
    return fresh;
  }

  saveDatabase(db = this.db) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    } catch {
      // ignore
    }
  }

  reset() {
    this.db = createInitialDatabase();
    this.saveDatabase(this.db);
    return { success: true, message: 'Mock database reset to initial seed state.' };
  }

  async handleRequest(endpoint, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const body = options.body ? JSON.parse(options.body) : {};
    const url = new URL('http://dummy' + endpoint);
    const path = url.pathname;
    const searchParams = url.searchParams;

    // Simulate realistic asynchronous network delay (15-50ms)
    await new Promise(resolve => setTimeout(resolve, 25));

    // 1. Auth endpoints
    if (path === '/auth/login' && method === 'POST') {
      const user = this.db.users.find(u => u.email.toLowerCase() === (body.email || '').toLowerCase()) || this.db.users[0];
      return {
        token: 'mock-jwt-token-' + user.id,
        user: { ...user }
      };
    }

    if (path === '/auth/me') {
      return this.db.users[0];
    }

    if (path === '/auth/logout') {
      return { message: 'Logged out successfully.' };
    }

    // 2. Hierarchy endpoints
    if (path === '/organizations') {
      return this.db.organizations;
    }

    if (path === '/regions') {
      return this.db.regions;
    }

    if (path === '/stores') {
      return this.db.stores;
    }

    if (path.startsWith('/stores/')) {
      const id = path.split('/')[2];
      return this.db.stores.find(s => s.id === id) || this.db.stores[0];
    }

    if (path === '/departments') {
      const storeId = searchParams.get('storeId');
      return storeId ? this.db.departments.filter(d => d.storeId === storeId) : this.db.departments;
    }

    if (path === '/assets') {
      const storeId = searchParams.get('storeId');
      return storeId ? this.db.assets.filter(a => a.storeId === storeId) : this.db.assets;
    }

    if (path === '/teams') {
      return this.db.teams;
    }

    // 3. Feedback endpoints
    if (path === '/feedback') {
      return {
        items: this.db.feedback,
        meta: { page: 1, limit: 50, total: this.db.feedback.length, totalPages: 1 }
      };
    }

    if (path === '/feedback/submit' && method === 'POST') {
      const newItem = {
        id: 'fb-user-' + Date.now(),
        organizationId: 'org-apex-01',
        storeId: body.storeId || 'store-104',
        channelType: body.channelType || 'MOBILE_APP',
        submitterType: body.submitterType || 'CUSTOMER',
        languageCode: body.languageCode || 'en',
        rawText: body.rawText,
        sentimentScore: -0.7,
        processingStatus: 'ANALYZED',
        submittedAt: new Date().toISOString(),
        aiInterpretation: {
          language: { code: body.languageCode || 'en', confidence: 0.98 },
          issueCategory: { value: 'FACILITIES_MAINTENANCE', confidence: 0.93 },
          intent: { value: 'REPORT_EQUIPMENT_FAILURE', confidence: 0.94 },
          safetyRelevance: { value: 'POTENTIAL_HAZARD', isSafetyHazard: true, confidence: 0.90 },
          location: { value: 'Store Floor', confidence: 0.88 },
          affectedEntity: { value: 'Equipment', confidence: 0.88 },
          overallConfidence: 0.91
        }
      };
      this.db.feedback.unshift(newItem);
      this.saveDatabase();
      return newItem;
    }

    if (path.startsWith('/feedback/')) {
      const id = path.split('/')[2];
      const item = this.db.feedback.find(f => f.id === id);
      return item || this.db.feedback[0];
    }

    // 4. Clusters
    if (path === '/clusters') {
      return this.db.clusters;
    }

    if (path === '/clusters/discover' && method === 'POST') {
      return this.db.clusters;
    }

    if (path.startsWith('/clusters/')) {
      const id = path.split('/')[2];
      const cl = this.db.clusters.find(c => c.id === id) || this.db.clusters[0];
      return {
        ...cl,
        feedbackItems: this.db.feedback
      };
    }

    // 5. Alerts
    if (path === '/alerts') {
      return this.db.alerts;
    }

    if (path.startsWith('/alerts/') && path.endsWith('/acknowledge') && method === 'POST') {
      const id = path.split('/')[2];
      const alt = this.db.alerts.find(a => a.id === id);
      if (alt) {
        alt.isAcknowledged = true;
        alt.status = 'ACKNOWLEDGED';
        this.saveDatabase();
        return alt;
      }
      return this.db.alerts[0];
    }

    if (path.startsWith('/alerts/') && path.endsWith('/escalate') && method === 'POST') {
      const id = path.split('/')[2];
      const alt = this.db.alerts.find(a => a.id === id);
      if (alt) {
        alt.status = 'ESCALATED';
        this.saveDatabase();
        return alt;
      }
      return this.db.alerts[0];
    }

    if (path.startsWith('/alerts/')) {
      const id = path.split('/')[2];
      return this.db.alerts.find(a => a.id === id) || this.db.alerts[0];
    }

    // 6. Issues
    if (path === '/issues') {
      return this.db.issues;
    }

    if (path.startsWith('/issues/') && path.endsWith('/status') && method === 'PATCH') {
      const id = path.split('/')[2];
      const iss = this.db.issues.find(i => i.id === id);
      if (iss) {
        iss.status = body.status;
        this.saveDatabase();
        return iss;
      }
      return this.db.issues[0];
    }

    if (path.startsWith('/issues/') && path.endsWith('/lineage')) {
      return {
        issueId: 'iss-demo-cooler-104',
        nodes: [
          { id: 'node-raw-01', label: 'Raw Feedback #1 (Mobile App)', type: 'FACT', description: 'Water pooling under dairy cooler in aisle 4', confidence: 1.0 },
          { id: 'node-raw-02', label: 'Raw Feedback #2 (Kiosk)', type: 'FACT', description: 'Charco de agua saliendo de nevera de lacteos', confidence: 1.0 },
          { id: 'node-und-01', label: 'AI Entity Extraction', type: 'HYPOTHESIS', description: 'Cooler 4B defrost malfunction', confidence: 0.95 },
          { id: 'node-alt-01', label: 'Poisson Anomaly Alert', type: 'HYPOTHESIS', description: '+8.49z velocity burst above 14d baseline', confidence: 0.94 },
          { id: 'node-pri-01', label: 'Deterministic Priority', type: 'FACT', description: 'Score 85 (P1_CRITICAL) via Safety Floor Override', confidence: 1.0 },
          { id: 'node-rou-01', label: 'Operational Dispatch', type: 'RECOMMENDATION', description: 'Regional HVAC with 30m emergency SLA', confidence: 0.98 },
          { id: 'node-act-01', label: 'Action Plan Authorized', type: 'RECOMMENDATION', description: 'Store Lead approved technician repair', confidence: 1.0 },
          { id: 'node-res-01', label: 'Technician Fix Executed', type: 'FACT', description: 'Replaced thermostat relay, dried tile floor', confidence: 1.0 },
          { id: 'node-out-01', label: 'Outcome Verified', type: 'FACT', description: '-100% complaint reduction post-intervention', confidence: 1.0 }
        ],
        edges: [
          { from: 'node-raw-01', to: 'node-und-01' },
          { from: 'node-raw-02', to: 'node-und-01' },
          { from: 'node-und-01', to: 'node-alt-01' },
          { from: 'node-alt-01', to: 'node-pri-01' },
          { from: 'node-pri-01', to: 'node-rou-01' },
          { from: 'node-rou-01', to: 'node-act-01' },
          { from: 'node-act-01', to: 'node-res-01' },
          { from: 'node-res-01', to: 'node-out-01' }
        ]
      };
    }

    if (path.startsWith('/issues/') && path.endsWith('/evidence')) {
      return [
        { id: 'ev-01', issueId: 'iss-demo-cooler-104', feedbackItemId: 'fb-demo-001', verbatimQuote: 'Water is pooling under the dairy cooler in aisle 4, someone is going to slip and fall!', confidenceScore: 0.99, createdAt: pastHour },
        { id: 'ev-02', issueId: 'iss-demo-cooler-104', feedbackItemId: 'fb-demo-002', verbatimQuote: 'piso muy resbaloso', confidenceScore: 0.96, createdAt: pastHour }
      ];
    }

    if (path.startsWith('/issues/') && path.endsWith('/recalculate-priority') && method === 'POST') {
      const id = path.split('/')[2];
      const iss = this.db.issues.find(i => i.id === id) || this.db.issues[0];
      iss.priorityScore = 85;
      iss.priorityTier = 'P1_CRITICAL';
      this.saveDatabase();
      return iss;
    }

    if (path.startsWith('/issues/')) {
      const id = path.split('/')[2];
      return this.db.issues.find(i => i.id === id) || this.db.issues[0];
    }

    // 7. Routing
    if (path.startsWith('/routing/issues/') && path.endsWith('/history')) {
      return [
        {
          id: 'rt-001',
          issueId: 'iss-demo-cooler-104',
          selectedTeamId: 'team-hvac-pnw',
          selectedTeamName: 'Regional Commercial HVAC & Refrigeration',
          routingStrategy: 'SAFETY_HAZARD_EMERGENCY_OVERRIDE',
          reason: 'Emergency safety hazard detected; routed directly to Store Facilities team with 30m emergency SLA.',
          confidence: 0.98,
          slaMinutes: 30,
          createdAt: pastHour
        }
      ];
    }

    if (path.startsWith('/routing/issues/') && path.endsWith('/reassign') && method === 'POST') {
      return {
        id: 'rt-reassign-' + Date.now(),
        issueId: path.split('/')[3],
        selectedTeamId: body.targetTeamId,
        routingStrategy: 'HUMAN_OVERRIDE',
        reason: body.reassignmentReason,
        confidence: 1.0,
        createdAt: new Date().toISOString()
      };
    }

    if (path.startsWith('/routing/issues/') && path.endsWith('/escalate') && method === 'POST') {
      return {
        id: 'rt-esc-' + Date.now(),
        issueId: path.split('/')[3],
        selectedTeamId: 'team-hvac-pnw',
        routingStrategy: 'ESCALATION',
        reason: body.escalationReason,
        confidence: 1.0,
        createdAt: new Date().toISOString()
      };
    }

    if (path === '/routing/triage-queue') {
      return [];
    }

    // Lineage Graph
    if ((path.startsWith('/lineage/issue/')) || (path.startsWith('/issues/') && path.endsWith('/lineage'))) {
      return {
        issueId: 'iss-demo-cooler-104',
        nodes: [
          { id: 'node-raw-01', label: 'Raw Feedback #1 (Mobile App)', type: 'FACT', description: 'Water pooling under dairy cooler in aisle 4', confidence: 1.0 },
          { id: 'node-raw-02', label: 'Raw Feedback #2 (Kiosk)', type: 'FACT', description: 'Charco de agua saliendo de nevera de lacteos', confidence: 1.0 },
          { id: 'node-und-01', label: 'AI Entity Extraction', type: 'HYPOTHESIS', description: 'Cooler 4B defrost malfunction', confidence: 0.95 },
          { id: 'node-alt-01', label: 'Poisson Anomaly Alert', type: 'HYPOTHESIS', description: '+8.49z velocity burst above 14d baseline', confidence: 0.94 },
          { id: 'node-pri-01', label: 'Deterministic Priority', type: 'FACT', description: 'Score 85 (P1_CRITICAL) via Safety Floor Override', confidence: 1.0 },
          { id: 'node-rou-01', label: 'Operational Dispatch', type: 'RECOMMENDATION', description: 'Regional HVAC with 30m emergency SLA', confidence: 0.98 },
          { id: 'node-act-01', label: 'Action Plan Authorized', type: 'RECOMMENDATION', description: 'Store Lead approved technician repair', confidence: 1.0 },
          { id: 'node-res-01', label: 'Technician Fix Executed', type: 'FACT', description: 'Replaced thermostat relay, dried tile floor', confidence: 1.0 },
          { id: 'node-out-01', label: 'Outcome Verified', type: 'FACT', description: '-100% complaint reduction post-intervention', confidence: 1.0 }
        ],
        edges: [
          { from: 'node-raw-01', to: 'node-und-01' },
          { from: 'node-raw-02', to: 'node-und-01' },
          { from: 'node-und-01', to: 'node-alt-01' },
          { from: 'node-alt-01', to: 'node-pri-01' },
          { from: 'node-pri-01', to: 'node-rou-01' },
          { from: 'node-rou-01', to: 'node-act-01' },
          { from: 'node-act-01', to: 'node-res-01' },
          { from: 'node-res-01', to: 'node-out-01' }
        ]
      };
    }

    // 8. Actions
    if (path === '/actions') {
      return this.db.actions;
    }

    if (path.startsWith('/actions/') && path.endsWith('/approve') && method === 'POST') {
      const id = path.split('/')[2];
      const act = this.db.actions.find(a => a.id === id) || this.db.actions[0];
      act.approvalStatus = 'APPROVED';
      act.status = 'IN_PROGRESS';
      this.saveDatabase();
      return act;
    }

    // 9. Resolutions
    if (path.startsWith('/resolutions/issue/')) {
      return this.db.resolutions;
    }

    if (path === '/resolutions' && method === 'POST') {
      const res = {
        id: 'res-new-' + Date.now(),
        issueId: body.issueId,
        performedByUserName: 'Carlos Gomez',
        workSummary: body.workSummary,
        partsReplaced: body.partsReplaced,
        rootCauseConfirmed: body.rootCauseConfirmed,
        cabinetTemperatureF: body.cabinetTemperatureF || 36.0,
        spoilageLossAmount: 0.0,
        status: 'VERIFIED',
        createdAt: new Date().toISOString()
      };
      this.db.resolutions.unshift(res);
      this.saveDatabase();
      return res;
    }

    // 10. Outcomes
    if (path === '/outcomes/dashboard') {
      return {
        totalClosedIssues: 14,
        resolutionVerificationRate: 1.0,
        averageTtrHours: 2.1,
        safetyIncidentRecurrenceRate: 0.0,
        verifiedSavingsEstimate: 9850.00,
        outcomes: this.db.outcomes
      };
    }

    if (path === '/outcomes') {
      return this.db.outcomes;
    }

    if (path.startsWith('/outcomes/issues/') && path.endsWith('/evaluate') && method === 'POST') {
      return this.db.outcomes[0];
    }

    if (path.startsWith('/outcomes/issues/')) {
      return this.db.outcomes[0];
    }

    // 11. Briefs
    if (path === '/briefs/latest') {
      return this.db.briefs[0];
    }

    if (path === '/briefs') {
      return this.db.briefs;
    }

    if (path === '/briefs/generate' && method === 'POST') {
      return this.db.briefs[0];
    }

    // 12. Investigation
    if (path.startsWith('/investigation/feedback/')) {
      const id = path.split('/')[3];
      return this.db.investigations[id] || {
        feedbackItemId: id,
        investigationStatus: 'SUFFICIENT',
        missingFields: [],
        questions: []
      };
    }

    if (path.startsWith('/investigation/questions/') && path.endsWith('/answer') && method === 'POST') {
      return { success: true, message: 'Answer recorded and feedback enriched.' };
    }

    // 13. Users, Roles & Matrix
    if (path === '/users') {
      return this.db.users;
    }

    if (path.startsWith('/users/')) {
      const id = path.split('/')[2];
      return this.db.users.find(u => u.id === id) || this.db.users[0];
    }

    if (path === '/roles') {
      return [
        { id: 'role-org-admin', name: 'ORGANIZATION_ADMIN', description: 'Full administrative access across enterprise hierarchy.' },
        { id: 'role-ops-manager', name: 'OPERATIONS_MANAGER', description: 'Cross-store operational supervision and resource allocation.' },
        { id: 'role-reg-manager', name: 'REGIONAL_MANAGER', description: 'Regional performance oversight and multi-store escalations.' },
        { id: 'role-store-manager', name: 'STORE_MANAGER', description: 'Frontline store management, action plan approval, and staff triage.' },
        { id: 'role-maintenance', name: 'MAINTENANCE_TEAM', description: 'Field remediation, repair logging, and IoT sensor verification.' },
        { id: 'role-analyst', name: 'ANALYST', description: 'Performance reporting, pattern recognition, and telemetry auditing.' },
        { id: 'role-viewer', name: 'VIEWER', description: 'Read-only visibility for corporate stakeholders.' }
      ];
    }

    if (path === '/roles/permissions-matrix') {
      return {
        roles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER'],
        permissions: [
          { module: 'Feedback Ingestion', actions: { ORGANIZATION_ADMIN: ['read', 'write', 'delete'], STORE_MANAGER: ['read', 'write'], VIEWER: ['read'] } },
          { module: 'Action Approval', actions: { ORGANIZATION_ADMIN: ['approve', 'reject'], STORE_MANAGER: ['approve', 'reject'], MAINTENANCE_TEAM: ['read'] } },
          { module: 'Remediation Logging', actions: { MAINTENANCE_TEAM: ['create', 'update'], STORE_MANAGER: ['verify'], VIEWER: ['read'] } }
        ]
      };
    }

    // Ownership mappings & Hierarchy Lineage
    if (path === '/ownership-mappings') {
      return [
        { id: 'om-01', storeId: 'store-104', domain: 'FACILITIES_MAINTENANCE', teamId: 'team-hvac-pnw', teamName: 'Regional Commercial HVAC & Refrigeration', primaryContact: 'Carlos Gomez', slaTier: 'EMERGENCY' },
        { id: 'om-02', storeId: 'store-104', domain: 'JANITORIAL_SANITATION', teamId: 'team-jan-104', teamName: 'Store 104 Janitorial & Sanitation', primaryContact: 'Elena Rostova', slaTier: 'HIGH' },
        { id: 'om-03', storeId: 'store-104', domain: 'POS_HARDWARE', teamId: 'team-it-na', teamName: 'Regional IT & POS Systems', primaryContact: 'Devon Miles', slaTier: 'STANDARD' }
      ];
    }

    if (path === '/hierarchy/trace') {
      return {
        organization: { id: 'org-apex-01', name: 'Apex Retail International' },
        region: { id: 'reg-pnw-01', name: 'Pacific Northwest Region' },
        store: { id: 'store-104', name: 'Apex Supercenter - Seattle Downtown', storeNumber: 104 },
        department: { id: 'dept-104-dairy', name: 'Dairy & Refrigerated' },
        asset: { id: 'asset-cooler-4b', name: 'Commercial Reach-in Dairy Cooler 4B' },
        responsibleTeam: { id: 'team-hvac-pnw', name: 'Regional Commercial HVAC & Refrigeration' }
      };
    }

    // Audit logs
    if (path === '/audit-logs') {
      const pastHour = new Date(Date.now() - 3600000).toISOString();
      return [
        { id: 'log-01', entityType: 'ISSUE', entityId: 'iss-demo-cooler-104', action: 'PRIORITY_SET_CRITICAL', performedBy: 'Deterministic Rule Engine', timestamp: pastHour },
        { id: 'log-02', entityType: 'ACTION', entityId: 'act-01', action: 'DISPATCH_APPROVED', performedBy: 'David Miller (STORE_MANAGER)', timestamp: pastHour },
        { id: 'log-03', entityType: 'RESOLUTION', entityId: 'res-01', action: 'REPAIR_VERIFIED', performedBy: 'Carlos Gomez (MAINTENANCE_TEAM)', timestamp: new Date().toISOString() }
      ];
    }

    // Personal / Home mode
    if (path === '/personal-home/appliances') {
      return [
        { id: 'app-01', name: 'Smart Inverter Refrigerator', brand: 'Samsung', model: 'RF28R7351SG', location: 'Kitchen', status: 'NORMAL', warrantyExpiry: '2027-11-20' },
        { id: 'app-02', name: 'Front Load Washer', brand: 'LG', model: 'WM4000HBA', location: 'Laundry Room', status: 'NORMAL', warrantyExpiry: '2026-08-15' },
        { id: 'app-03', name: 'Central HVAC Heat Pump', brand: 'Carrier', model: 'Infinity 20', location: 'Basement', status: 'NEEDS_FILTER', warrantyExpiry: '2029-03-10' }
      ];
    }

    if (path === '/personal-home/tickets') {
      return [
        { id: 'tkt-01', applianceId: 'app-03', title: 'Seasonal Air Filter Replacement', priority: 'LOW', status: 'SCHEDULED', nextServiceDate: '2026-11-01' }
      ];
    }

    // 14. Multilingual
    if (path === '/multilingual/benchmark') {
      return {
        supportedLanguages: ['en', 'es', 'fr', 'de', 'hi', 'ta', 'te', 'kn', 'bn', 'gu', 'ml', 'pa'],
        accuracyRate: 0.985,
        testCasesEvaluated: 48
      };
    }

    if (path === '/multilingual/test-cases') {
      return [
        { id: 'tc-01', text: 'Water is pooling under the dairy cooler in aisle 4, someone is going to slip and fall!', language: 'en', category: 'FACILITIES_MAINTENANCE' },
        { id: 'tc-02', text: 'Charco de agua saliendo de nevera de lacteos en pasillo 4', language: 'es', category: 'FACILITIES_MAINTENANCE' },
        { id: 'tc-03', text: 'Fuite d\'eau sous le frigo des produits laitiers allée 4', language: 'fr', category: 'FACILITIES_MAINTENANCE' },
        { id: 'tc-04', text: 'Wasser läuft unter dem Kühlregal in Gang 4 aus, Rutschgefahr!', language: 'de', category: 'FACILITIES_MAINTENANCE' },
        { id: 'tc-05', text: 'Aisle 4 dairy cooler ke paas paani phail gaya hai, koi gir sakta hai', language: 'hi', category: 'FACILITIES_MAINTENANCE' }
      ];
    }

    if (path === '/multilingual/parse' && method === 'POST') {
      return {
        detectedLanguage: body.languageHint || 'en',
        confidence: 0.98,
        translatedText: body.text,
        entities: [
          { entity: 'dairy cooler', category: 'EQUIPMENT' },
          { entity: 'aisle 4', category: 'LOCATION' },
          { entity: 'slip and fall hazard', category: 'SAFETY_RISK' }
        ]
      };
    }

    // 15. Demo
    if (path === '/demo/scenario') {
      return {
        scenarioId: 'retail_cold_chain_failure',
        title: 'Refrigeration Failure & Sales Floor Slip Hazard',
        storeName: 'Apex Supercenter - Seattle Downtown',
        storeNumber: 104,
        department: 'Dairy & Refrigerated',
        targetAsset: 'Commercial Reach-in Dairy Cooler 4B'
      };
    }

    if (path === '/demo/status') {
      return {
        demonstrationId: 'demo-run-init',
        status: 'READY',
        currentStageIndex: 14,
        currentStageCode: 'STAGE_15'
      };
    }

    if (path === '/demo/run' && method === 'POST') {
      return {
        demonstrationId: 'demo-run-' + Date.now().toString(16),
        status: 'COMPLETED',
        totalDurationMs: 28.42,
        stages: [
          { stageCode: 'STAGE_01', title: 'Historical Baseline Seeding', status: 'COMPLETED', durationMs: 5.7, summary: 'Seeded 5 baseline maintenance records over 14-day history.' },
          { stageCode: 'STAGE_02', title: 'Raw Feedback Ingestion', status: 'COMPLETED', durationMs: 1.2, summary: 'Ingested 6 frontline reports in English, Spanish, French, Hinglish, German.' },
          { stageCode: 'STAGE_03', title: 'AI Operational Understanding', status: 'COMPLETED', durationMs: 0.1, summary: 'Extracted refrigeration failure entities and active slip & fall risk.' },
          { stageCode: 'STAGE_04', title: 'Investigation Follow-Up', status: 'COMPLETED', durationMs: 1.5, summary: 'Clarified missing asset context: Walk-in Cooler 104-B.' },
          { stageCode: 'STAGE_05', title: 'Semantic Issue Clustering', status: 'COMPLETED', durationMs: 1.0, summary: 'Synthesized 6 multilingual feedback items into cluster cl-demo-cooler-104.' },
          { stageCode: 'STAGE_06', title: 'Emerging Issue Anomaly Detection', status: 'COMPLETED', durationMs: 1.4, summary: 'Detected Poisson velocity spike (+8.49z above baseline).' },
          { stageCode: 'STAGE_07', title: 'Deterministic Priority Analytics', status: 'COMPLETED', durationMs: 1.1, summary: 'Calculated score 85/100 (P1_CRITICAL) via direct safety floor.' },
          { stageCode: 'STAGE_08', title: 'Traceable Evidence Lineage', status: 'COMPLETED', durationMs: 1.1, summary: 'Constructed 18-node DAG classifying FACT vs HYPOTHESIS vs RECOMMENDATION.' },
          { stageCode: 'STAGE_09', title: 'Intelligent Operational Routing', status: 'COMPLETED', durationMs: 0.7, summary: 'Dispatched to Regional Commercial HVAC with 30m emergency SLA.' },
          { stageCode: 'STAGE_10', title: 'Action Plan & Store Manager Approval', status: 'COMPLETED', durationMs: 0.7, summary: 'Store Manager approved emergency technician dispatch.' },
          { stageCode: 'STAGE_11', title: 'Real-Time SLA Tracking', status: 'COMPLETED', durationMs: 0.1, summary: 'Technician on-site within 16m; SLA met with 14m buffer.' },
          { stageCode: 'STAGE_12', title: 'Technician Remediation & Repair', status: 'COMPLETED', durationMs: 0.8, summary: 'Replaced faulty thermostat relay; cabinet restored to 36.0°F.' },
          { stageCode: 'STAGE_13', title: 'Automated System Verification', status: 'COMPLETED', durationMs: 0.4, summary: 'IoT sensor telemetry audited: 36.2°F stable, moisture sensors dry.' },
          { stageCode: 'STAGE_14', title: 'Post-Intervention Outcome Measurement', status: 'COMPLETED', durationMs: 7.5, summary: 'Confirmed -100% complaint reduction post-intervention; status CLOSED.' },
          { stageCode: 'STAGE_15', title: 'Management Intelligence Brief', status: 'COMPLETED', durationMs: 4.6, summary: 'Synthesized executive brief with 100% grounded facts.' }
        ]
      };
    }

    if (path === '/demo/reset' && method === 'POST') {
      this.reset();
      return { success: true, message: 'Demo state reset successfully.' };
    }

    // Default fallback
    return { success: true, data: [] };
  }
}

export const mockBackend = new MockBackend();
