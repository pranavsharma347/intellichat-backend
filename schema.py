from pydantic import BaseModel, EmailStr,Field
from datetime import datetime
from typing import Optional


# ===== User Schemas =====

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)

class Login(BaseModel):
    username:str
    password:str

class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    username: str | None = None

class UserCreate(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True   


# ===== Conversation Schemas =====

class ConversationCreate(BaseModel):
    user_email: EmailStr
    title: Optional[str] = "New Chat"

class ConversationUpdate(BaseModel):
    title: str = Field(..., max_length=100)

class ConversationResponse(BaseModel):
    id: str
    user_email: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Message Schemas =====

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: str
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ===== New Chat Scemas =====

class NewChatRequest(BaseModel):
    content: str  


class NewChatResponse(BaseModel):
    conversation_id: str
    title: str
    answer: str


# ===== Reset Password Schemas =====
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class TokenCheckRequest(BaseModel):
    token: str

### ===== User Verification Schemas =====
class VerifyEmailRequest(BaseModel):
    token: str
 
 
class ResendVerificationRequest(BaseModel):
    email: EmailStr
 