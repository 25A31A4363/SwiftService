from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=6)

class UserCreate(BaseModel):
    organizationId: str
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=6)
    fullName: str = Field(..., min_length=2, max_length=120)
    role: str = Field(..., min_length=2, max_length=50)
    storeId: Optional[str] = None
    regionId: Optional[str] = None
    teamId: Optional[str] = None
    isActive: Optional[bool] = True

class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: Optional[str] = Field(None, min_length=6)
    fullName: Optional[str] = Field(None, min_length=2, max_length=120)
    role: Optional[str] = Field(None, min_length=2, max_length=50)
    storeId: Optional[str] = None
    regionId: Optional[str] = None
    teamId: Optional[str] = None
    isActive: Optional[bool] = None

class UserResponse(BaseModel):
    id: str
    organizationId: str
    email: str
    fullName: str
    role: str
    storeId: Optional[str] = None
    storeName: Optional[str] = None
    regionId: Optional[str] = None
    regionName: Optional[str] = None
    teamId: Optional[str] = None
    teamName: Optional[str] = None
    isActive: bool
    lastLoginAt: Optional[str] = None
    createdAt: str
    updatedAt: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse
    expiresIn: str

class ProfileUpdateRequest(BaseModel):
    fullName: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[str] = Field(None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class ChangePasswordRequest(BaseModel):
    currentPassword: str = Field(..., min_length=1, description="Existing account password for verification")
    newPassword: str = Field(..., min_length=8, description="New password, minimum 8 characters")
    confirmPassword: Optional[str] = None
