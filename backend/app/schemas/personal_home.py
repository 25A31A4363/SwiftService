from pydantic import BaseModel, Field
from typing import Optional

class PersonalApplianceCreate(BaseModel):
    applianceType: str = Field(..., pattern="^(TV|REFRIGERATOR|WASHING_MACHINE|AC)$")
    brand: str = Field(..., min_length=2)
    modelNumber: Optional[str] = None
    serialNumber: Optional[str] = None
    purchaseDate: Optional[str] = None
    warrantyUntil: Optional[str] = None

class PersonalApplianceResponse(BaseModel):
    id: str
    userId: str
    applianceType: str
    brand: str
    modelNumber: Optional[str] = None
    serialNumber: Optional[str] = None
    purchaseDate: Optional[str] = None
    warrantyUntil: Optional[str] = None
    createdAt: str
    updatedAt: str

class PersonalTicketCreate(BaseModel):
    applianceId: str
    complaintDescription: str = Field(..., min_length=5)
    classifiedCategory: Optional[str] = "GENERAL_SERVICE"
    routedServiceChannel: Optional[str] = "AUTHORIZED_SERVICE_CENTER"

class PersonalTicketResponse(BaseModel):
    id: str
    applianceId: str
    userId: str
    complaintDescription: str
    classifiedCategory: str
    routedServiceChannel: str
    status: str
    externalReferenceId: Optional[str] = None
    createdAt: str
    updatedAt: str
