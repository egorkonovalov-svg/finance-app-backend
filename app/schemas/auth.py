from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SocialAuthRequest(BaseModel):
    provider: str = Field(pattern="^(google|apple)$")
    id_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    avatar: str | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str | None = None


class VerificationPendingResponse(BaseModel):
    session_id: str
    message: str


class VerifyCodeRequest(BaseModel):
    session_id: str
    code: str = Field(min_length=6, max_length=6)


class ResendCodeRequest(BaseModel):
    session_id: str
