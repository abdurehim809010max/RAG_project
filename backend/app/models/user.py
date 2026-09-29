"""User contract used by authentication until the database adapter is connected."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    email: str = Field(min_length=3, max_length=320)
    password_hash: str
    is_active: bool = True
    created_at: datetime


class UserPublic(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime


class UserRegistration(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
