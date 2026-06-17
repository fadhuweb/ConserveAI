from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    username: str
    role: str
    park_id: str | None
    must_change_password: bool = False
    message: str = "Login successful"


class CreateUserRequest(BaseModel):
    username: str
    full_name: str
    email: str | None = None      # required for managers — the temp password is emailed here
    role: str = "manager"         # "manager" or "admin"
    park_id: str | None = None    # required for managers; ignored for admins
    phone: str | None = None      # stored as contact; not used for delivery (SMS out of scope)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str
    park_id: str | None
    email: str | None
    phone: str | None
    must_change_password: bool
    is_active: bool = True

    model_config = {"from_attributes": True}


class SetActiveRequest(BaseModel):
    is_active: bool