from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OrganizationBrief(BaseModel):
    id: str
    name: str
    slug: str

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    registration_code: str = Field(min_length=4, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None


class SwitchOrganizationRequest(BaseModel):
    organization_id: str


class ValidateCodeRequest(BaseModel):
    registration_code: str = Field(min_length=4, max_length=64)


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    organization: OrganizationBrief | None = None
    active_organization: OrganizationBrief | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthConfigResponse(BaseModel):
    auth_required: bool
    authenticated: bool


class CreateRegistrationCodeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=64)
    organization_id: str
    label: str | None = Field(default=None, max_length=120)
