from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentAuth, get_optional_auth, require_auth, require_user
from app.models.user import User
from app.schemas.auth import (
    AuthConfigResponse,
    CreateRegistrationCodeRequest,
    LoginRequest,
    OrganizationBrief,
    ProfileUpdate,
    RegisterRequest,
    SwitchOrganizationRequest,
    UserResponse,
    ValidateCodeRequest,
)
from app.services import auth_service
from app.services.organization_service import (
    effective_organization_id,
    ensure_registration_code,
    get_organization_by_id,
    is_super_admin,
    list_organizations,
    resolve_registration_code,
)

router = APIRouter(prefix=settings.route_prefix("/auth"), tags=["auth"])


async def _user_response(db: AsyncSession, auth: CurrentAuth) -> UserResponse:
    org_id = effective_organization_id(auth.user, auth.session)
    active = None
    if org_id:
        if auth.user.organization and auth.user.organization.id == org_id:
            active = OrganizationBrief.model_validate(auth.user.organization)
        else:
            org = await get_organization_by_id(db, org_id)
            if org:
                active = OrganizationBrief.model_validate(org)

    org_brief = (
        OrganizationBrief.model_validate(auth.user.organization)
        if auth.user.organization
        else None
    )
    return UserResponse(
        id=auth.user.id,
        email=auth.user.email,
        display_name=auth.user.display_name,
        role=auth.user.role,
        organization=org_brief,
        active_organization=active,
        created_at=auth.user.created_at,
    )


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config(auth: CurrentAuth | None = Depends(get_optional_auth)):
    return AuthConfigResponse(
        auth_required=settings.AUTH_REQUIRED,
        authenticated=auth is not None,
    )


@router.get("/me", response_model=UserResponse | None)
async def me(
    auth: CurrentAuth | None = Depends(get_optional_auth),
    db: AsyncSession = Depends(get_db),
):
    if auth is None:
        return None
    return await _user_response(db, auth)


@router.get("/organizations", response_model=list[OrganizationBrief])
async def list_all_organizations(
    auth: CurrentAuth = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if not is_super_admin(auth.user):
        raise HTTPException(status_code=403, detail="Super admin only")
    orgs = await list_organizations(db)
    return [OrganizationBrief.model_validate(o) for o in orgs]


@router.post("/active-organization", response_model=UserResponse)
async def switch_active_organization(
    data: SwitchOrganizationRequest,
    auth: CurrentAuth = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if not is_super_admin(auth.user):
        raise HTTPException(status_code=403, detail="Super admin only")

    org = await get_organization_by_id(db, data.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    auth.session.active_organization_id = org.id
    await db.flush()
    return await _user_response(db, auth)


@router.post("/registration-codes", status_code=201)
async def create_registration_code(
    data: CreateRegistrationCodeRequest,
    auth: CurrentAuth = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if not is_super_admin(auth.user):
        raise HTTPException(status_code=403, detail="Super admin only")

    org = await get_organization_by_id(db, data.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        await ensure_registration_code(
            db,
            organization=org,
            raw_code=data.code,
            label=data.label,
        )
    except ValueError as exc:
        if str(exc) == "code_conflict":
            raise HTTPException(
                status_code=409, detail="Code already used by another organization"
            ) from exc
        raise

    return {"code": data.code.strip(), "organization_id": org.id, "organization_name": org.name}


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.register_user(
            db,
            email=str(data.email),
            password=data.password,
            display_name=data.display_name,
            registration_code=data.registration_code,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "email_taken":
            raise HTTPException(status_code=409, detail="Email already registered") from exc
        if code == "invalid_code":
            raise HTTPException(status_code=400, detail="Invalid or inactive registration code") from exc
        raise

    token, session = await auth_service.create_session(db, user)
    response.set_cookie(value=token, **auth_service.session_cookie_kwargs())
    auth = CurrentAuth(user=user, session=session)
    return await _user_response(db, auth)


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.authenticate_user(
        db, email=str(data.email), password=data.password
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.organization_id is None:
        raise HTTPException(
            status_code=403,
            detail="Account has no organization. Contact administrator.",
        )

    token, session = await auth_service.create_session(db, user)
    response.set_cookie(value=token, **auth_service.session_cookie_kwargs())
    auth = CurrentAuth(user=user, session=session)
    return await _user_response(db, auth)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(auth_service.SESSION_COOKIE)
    await auth_service.revoke_session(db, token)
    response.delete_cookie(
        key=auth_service.SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdate,
    auth: CurrentAuth = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    user = auth.user
    if data.display_name is not None:
        name = data.display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Display name cannot be empty")
        user.display_name = name

    if data.email is not None:
        new_email = str(data.email).strip().lower()
        if new_email != user.email:
            existing = await auth_service.get_user_by_email(db, new_email)
            if existing and existing.id != user.id:
                raise HTTPException(status_code=409, detail="Email already registered")
            user.email = new_email

    await db.flush()
    await db.refresh(user, attribute_names=["organization"])
    return await _user_response(db, auth)


@router.post("/validate-code")
async def validate_registration_code(
    data: ValidateCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        org = await resolve_registration_code(db, data.registration_code)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or inactive registration code") from None
    return {
        "valid": True,
        "organization": OrganizationBrief.model_validate(org),
    }
