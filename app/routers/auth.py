import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    SocialAuthRequest,
    UserResponse,
)
from app.services.auth import (
    DEFAULT_CATEGORIES,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


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


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    await db.flush()

    await _seed_categories(db, user.id)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


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
        # Apple ID token verification would go here.
        # For now, decode the JWT payload without verification for development.
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
        user = User(email=email, name=name, provider=body.provider)
        db.add(user)
        await db.flush()
        await _seed_categories(db, user.id)
        await db.commit()
        await db.refresh(user)
    else:
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
    # Stateless JWT -- client discards the token.
    # A production system would add the token to a blocklist here.
    return None
