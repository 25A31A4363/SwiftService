"""
Pydantic Schemas for Customer Complaint Portal & Resolution Tracking
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CustomerRegisterRequest(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = Field(None, max_length=25)

class CustomerRegisterResponse(BaseModel):
    message: str
    email: str
    isVerified: bool = False
    expiresInMinutes: int = 10
    emailDelivery: Dict[str, Any]
    devOtpCode: Optional[str] = None

class VerifyOtpRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    otp: str = Field(..., min_length=6, max_length=6)

class ResendOtpRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class ComplaintCreate(BaseModel):
    category: str = Field(..., min_length=2, max_length=64)
    orderNumber: Optional[str] = Field(None, max_length=64)
    storeId: Optional[str] = Field(None, max_length=64)
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    attachmentUrl: Optional[str] = None
    attachmentName: Optional[str] = None

class ComplaintStatusUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(SUBMITTED|UNDER_REVIEW|IN_PROGRESS|RESOLVED|CLOSED)$")
    assignedTeamId: Optional[str] = None
    investigationNotes: Optional[str] = None
    resolutionSummary: Optional[str] = None

class ComplaintTimelineEntry(BaseModel):
    status: str
    timestamp: str
    actor: str
    note: Optional[str] = None

class ComplaintResponse(BaseModel):
    id: str
    referenceNumber: str
    customerId: str
    customerName: str
    customerEmail: str
    customerPhone: Optional[str] = None
    category: str
    orderNumber: Optional[str] = None
    storeId: Optional[str] = None
    storeName: Optional[str] = None
    subject: str
    description: str
    attachmentUrl: Optional[str] = None
    attachmentName: Optional[str] = None
    status: str
    priority: str
    assignedTeamId: Optional[str] = None
    assignedTeamName: Optional[str] = None
    assignedToUserId: Optional[str] = None
    assignedToName: Optional[str] = None
    investigationNotes: Optional[str] = None
    resolutionSummary: Optional[str] = None
    feedbackItemId: Optional[str] = None
    issueId: Optional[str] = None
    timeline: List[ComplaintTimelineEntry] = []
    createdAt: str
    updatedAt: str

class ComplaintPublicTracking(BaseModel):
    id: str
    referenceNumber: str
    customerName: str
    category: str
    orderNumber: Optional[str] = None
    storeName: Optional[str] = None
    subject: str
    description: str
    attachmentName: Optional[str] = None
    status: str
    priority: str
    assignedTeamName: Optional[str] = None
    resolutionSummary: Optional[str] = None
    timeline: List[ComplaintTimelineEntry] = []
    createdAt: str
    updatedAt: str
