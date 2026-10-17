"""
R5 Operational Intelligence Platform - Feedback Connectors Architecture
Extensible connector framework allowing new channels (e.g. WhatsApp, Slack, IoT, Zendesk)
to be registered dynamically without modifying the ingestion core.
"""

from abc import ABC
from typing import Dict, Any, Optional, List
from backend.app.core.errors import ValidationError

class BaseFeedbackConnector(ABC):
    """Abstract base class for all operational feedback connectors."""
    
    channel_type: str = "BASE"
    default_submitter: str = "ANONYMOUS"
    default_privacy: str = "INTERNAL"

    def parse_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw input into canonical feedback dictionary before pipeline processing."""
        return {
            "channelType": raw_payload.get("channelType") or self.channel_type,
            "sourceType": raw_payload.get("sourceType") or raw_payload.get("channelType") or self.channel_type,
            "submitterType": raw_payload.get("submitterType") or self.default_submitter,
            "privacyClassification": raw_payload.get("privacyClassification") or self.default_privacy,
            "rawText": raw_payload.get("rawText", "").strip(),
            "languageCode": raw_payload.get("languageCode") or "auto",
            "storeId": raw_payload.get("storeId"),
            "regionId": raw_payload.get("regionId"),
            "organizationId": raw_payload.get("organizationId"),
            "departmentId": raw_payload.get("departmentId"),
            "submittedAt": raw_payload.get("submittedAt"),
            "metadata": raw_payload.get("metadata") or {}
        }

    def validate(self, parsed: Dict[str, Any]) -> None:
        """Channel-specific validation rules."""
        raw_text = parsed.get("rawText", "")
        if not raw_text or len(raw_text) < 3:
            raise ValidationError(f"Feedback text for channel '{self.channel_type}' must be at least 3 characters long.")
        if len(raw_text) > 10000:
            raise ValidationError(f"Feedback text for channel '{self.channel_type}' exceeds maximum 10,000 characters.")


class ManualEntryConnector(BaseFeedbackConnector):
    """Direct manual entry by frontline associates or store staff."""
    channel_type = "MANUAL_ENTRY"
    default_submitter = "STORE_ASSOCIATE"
    default_privacy = "INTERNAL"


class CustomerComplaintConnector(BaseFeedbackConnector):
    """Customer grievances, service desk complaints, and guest feedback."""
    channel_type = "CUSTOMER_COMPLAINT"
    default_submitter = "CUSTOMER"
    default_privacy = "INTERNAL"


class EmployeeFeedbackConnector(BaseFeedbackConnector):
    """Internal employee suggestions, shift observations, and workplace reporting."""
    channel_type = "EMPLOYEE_FEEDBACK"
    default_submitter = "EMPLOYEE"
    default_privacy = "CONFIDENTIAL"


class MaintenanceReportConnector(BaseFeedbackConnector):
    """Technician observations, refrigeration logs, and facility walkthroughs."""
    channel_type = "MAINTENANCE_REPORT"
    default_submitter = "MAINTENANCE_TECH"
    default_privacy = "INTERNAL"


class SurveyResponseConnector(BaseFeedbackConnector):
    """Open-ended CSAT/NPS survey responses and digital questionnaire feedback."""
    channel_type = "SURVEY_RESPONSE"
    default_submitter = "CUSTOMER"
    default_privacy = "INTERNAL"


class OperationalNoteConnector(BaseFeedbackConnector):
    """Shift logs, manager pass-down notes, audit remarks, and supervisor logs."""
    channel_type = "OPERATIONAL_NOTE"
    default_submitter = "STORE_MANAGER"
    default_privacy = "INTERNAL"


class BulkImportConnector(BaseFeedbackConnector):
    """Bulk ingested entries from CSV or JSON batches."""
    channel_type = "BULK_IMPORT"
    default_submitter = "ANONYMOUS"
    default_privacy = "INTERNAL"


# Legacy / Kiosk Connectors (Maintaining 100% backward compatibility)
class QRKioskConnector(BaseFeedbackConnector):
    channel_type = "QR_KIOSK"
    default_submitter = "CUSTOMER"
    default_privacy = "PUBLIC"

class AssociateAppConnector(BaseFeedbackConnector):
    channel_type = "ASSOCIATE_APP"
    default_submitter = "EMPLOYEE"
    default_privacy = "INTERNAL"

class CustomerVoiceConnector(BaseFeedbackConnector):
    channel_type = "CUSTOMER_VOICE"
    default_submitter = "CUSTOMER"
    default_privacy = "INTERNAL"

class WebFormConnector(BaseFeedbackConnector):
    channel_type = "WEB_FORM"
    default_submitter = "CUSTOMER"
    default_privacy = "PUBLIC"

class POSExceptionConnector(BaseFeedbackConnector):
    channel_type = "POS_EXCEPTION"
    default_submitter = "STORE_ASSOCIATE"
    default_privacy = "INTERNAL"


class ConnectorRegistry:
    """Central registry for pluggable ingestion connectors."""
    
    _connectors: Dict[str, BaseFeedbackConnector] = {}

    @classmethod
    def register(cls, connector: BaseFeedbackConnector) -> None:
        cls._connectors[connector.channel_type.upper()] = connector

    @classmethod
    def get(cls, channel_type: Optional[str]) -> BaseFeedbackConnector:
        if not channel_type:
            return cls._connectors["MANUAL_ENTRY"]
        
        normalized = channel_type.upper()
        if normalized in cls._connectors:
            return cls._connectors[normalized]
        
        # Fallback to ManualEntryConnector if unknown channel
        return cls._connectors.get("MANUAL_ENTRY", ManualEntryConnector())

    @classmethod
    def supported_channels(cls) -> List[str]:
        return list(cls._connectors.keys())


# Auto-register standard channels
_BUILTIN_CONNECTORS = [
    ManualEntryConnector(),
    CustomerComplaintConnector(),
    EmployeeFeedbackConnector(),
    MaintenanceReportConnector(),
    SurveyResponseConnector(),
    OperationalNoteConnector(),
    BulkImportConnector(),
    QRKioskConnector(),
    AssociateAppConnector(),
    CustomerVoiceConnector(),
    WebFormConnector(),
    POSExceptionConnector()
]

for conn_instance in _BUILTIN_CONNECTORS:
    ConnectorRegistry.register(conn_instance)
