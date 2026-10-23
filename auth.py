from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typer import models
import models,security
from database import get_db
from hashing import Hash
import schema
import os
import email_service
from fastapi import BackgroundTasks
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.username.lower()).first()

    if not user or not user.password or not Hash.verify(user.password, request.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email first. Check your inbox and Spam folder.")
    
    token = security.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot-password")
def forgot_password(
    request: schema.ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:

        user = db.query(models.User).filter(models.User.email == request.email.lower()).first()

        if user and user.password:
            token = security.create_reset_token(user.email, user.password)

            frontend = os.getenv("FRONTEND_URL", "http://localhost:5173")
            link = f"{frontend}/reset-password?token={token}"
            background_tasks.add_task(email_service.send_reset_email, user.email, link)

        return {"message": "if email is registered, reset link has been sent."}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")



@router.post("/reset-password")
def reset_password(request: schema.ResetPasswordRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=400, detail="Invalid or expired reset link")

    payload = security.verify_reset_token(request.token)
    if not payload:
        raise invalid

    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if not user or not user.password or user.password[-10:] != payload["pwd"]:
        raise invalid                                   

    user.password = Hash.bcrypt(request.new_password)   
    db.commit()
    return {"message": "Password updated. Ab naye password se login karo."}



@router.post("/reset-password")
def reset_password(request: schema.ResetPasswordRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=400, detail="Invalid or expired reset link")

    payload = security.verify_reset_token(request.token)
    if not payload:
        raise invalid

    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if not user or not user.password or user.password[-10:] != payload["pwd"]:
        raise invalid                                   

    user.password = Hash.bcrypt(request.new_password)   
    db.commit()
    return {"message": "Password updated. Now login with new password."}


@router.post("/reset-password/check")
def check_reset_token(request: schema.TokenCheckRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=400, detail="Invalid or expired reset link")

    payload = security.verify_reset_token(request.token)
    if not payload:
        raise invalid

    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if not user or not user.password or user.password[-10:] != payload["pwd"]:
        raise invalid

    return {"valid": True}


#for user verification
@router.post("/verify-email")
def verify_email(request: schema.VerifyEmailRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=400, detail="Invalid or expired verification link")
 
    payload = security.verify_verify_token(request.token)
    if not payload:
        raise invalid
 
    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if not user:
        raise invalid
 
    if not user.is_verified:
        user.is_verified = True
        db.commit()
    return {"message": "Email verified. You can now log in."}



@router.post("/resend-verification")
def resend_verification(
    request: schema.ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == request.email.lower()).first()
    if user and not user.is_verified:
        token = security.create_verify_token(user.email)
        frontend = os.getenv("FRONTEND_URL", "http://localhost:5173")
        link = f"{frontend}/verify-email?token={token}"
        background_tasks.add_task(email_service.send_verification_email, user.email, link)
 
    return {"message": "If this email needs verification, a new link has been sent."}
