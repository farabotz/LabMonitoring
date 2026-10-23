from pydantic import BaseModel, Field
from typing import Literal


class Credentials(BaseModel):
    nim: str = Field(min_length=1, max_length=40, pattern=r"^[\w.-]+$")
    password: str = Field(min_length=1, max_length=256)


class UserCreate(Credentials):
    password: str = Field(min_length=12, max_length=256)
    name: str = Field(min_length=1, max_length=120)
    role: Literal["student", "operator", "admin"] = "student"


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class UserState(BaseModel):
    active: bool


class EnrollmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    veyon_host: str = Field(default="", max_length=253, pattern=r"^[a-zA-Z0-9.:_-]*$")


class DeviceEnroll(BaseModel):
    token: str = Field(min_length=20, max_length=150)
    device_id: str = Field(pattern=r"^[a-f0-9-]{36}$")


class PasswordLogin(Credentials):
    request_key: str = Field(min_length=16, max_length=100)


class Heartbeat(BaseModel):
    boot_id: str = Field(min_length=1, max_length=80)


class Reason(BaseModel):
    reason: str = Field(min_length=5, max_length=200)


class FaceChallenge(BaseModel):
    nim: str = Field(min_length=1, max_length=40)


class DeviceUpdate(BaseModel):
    problem: str = Field(default="", max_length=240)
    active: bool = True
    veyon_host: str = Field(default="", max_length=253, pattern=r"^[a-zA-Z0-9.:_-]*$")
