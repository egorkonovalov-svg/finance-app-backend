from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.category import Category
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    ResendCodeRequest,
    SignupRequest,
    SocialAuthRequest,
    UserResponse,
    VerificationPendingResponse,
    VerifyCodeRequest,
)
from app.services.auth import (
    DEFAULT_CATEGORIES,
    create_access_token,
    create_verification,
    hash_password,
    validate_verification_code,
    verify_password,
)
from app.services.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["Auth"])

MAX_RESENDS = 3


async def _seed_categories(db: AsyncSession, user_id) -> None:
    for cat in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user_id, **cat))


def _build_auth_response(user: User, token: str) -> AuthResponse:
    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar=user.avatar,
        ),
        access_token=token,
    )


@router.post(
    "/signup",
    response_model=VerificationPendingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing and existing.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    if existing and not existing.is_verified:
        # Re-use the unverified user row, update password/name in case they changed
        existing.password_hash = hash_password(body.password)
        existing.name = body.name
        user = existing
        await db.flush()
    else:
        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            name=body.name,
            is_verified=False,
        )
        db.add(user)
        await db.flush()

    session_id, code = await create_verification(db, user.id, "signup")
    await send_verification_email(user.email, code)

    return VerificationPendingResponse(
        session_id=session_id,
        message="Verification code sent to your email",
    )


@router.post("/login", response_model=VerificationPendingResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please sign up again.",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    session_id, code = await create_verification(db, user.id, "login")
    await send_verification_email(user.email, code)

    return VerificationPendingResponse(
        session_id=session_id,
        message="Verification code sent to your email",
    )


@router.post("/verify-code", response_model=AuthResponse)
async def verify_code(body: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    record = await validate_verification_code(db, body.session_id, body.code)

    result = await db.execute(select(User).where(User.id == record.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if record.purpose == "signup" and not user.is_verified:
        user.is_verified = True
        await _seed_categories(db, user.id)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


@router.post("/resend-code", response_model=VerificationPendingResponse)
async def resend_code(body: ResendCodeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.id == UUID(body.session_id)
        )
    )
    old_record = result.scalar_one_or_none()
    if not old_record or old_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification session",
        )

    # Count resends: how many codes exist for this user+purpose created after the original
    resend_count_result = await db.execute(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == old_record.user_id,
            VerificationCode.purpose == old_record.purpose,
            VerificationCode.created_at >= old_record.created_at,
        )
    )
    resend_count = len(resend_count_result.scalars().all())
    if resend_count > MAX_RESENDS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum resend limit reached. Please start over.",
        )

    old_record.used = True
    await db.flush()

    user_result = await db.execute(
        select(User).where(User.id == old_record.user_id)
    )
    user = user_result.scalar_one()

    session_id, code = await create_verification(db, user.id, old_record.purpose)
    await send_verification_email(user.email, code)

    return VerificationPendingResponse(
        session_id=session_id,
        message="New verification code sent to your email",
    )


@router.post("/social", response_model=AuthResponse)
async def social_auth(body: SocialAuthRequest, db: AsyncSession = Depends(get_db)):
    email: str | None = None
    name: str | None = None

    if body.provider == "google":
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={body.id_token}"
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID token",
            )
        info = resp.json()
        email = info.get("email")
        name = info.get("name")

    elif body.provider == "apple":
        from jose import jwt as jose_jwt

        try:
            payload = jose_jwt.get_unverified_claims(body.id_token)
            email = payload.get("email")
            name = payload.get("name")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Apple ID token",
            )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not extract email from token",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email, name=name, provider=body.provider, is_verified=True
        )
        db.add(user)
        await db.flush()
        await _seed_categories(db, user.id)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.is_verified:
            user.is_verified = True
        await db.commit()

    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        avatar=current_user.avatar,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user)):
    return None
