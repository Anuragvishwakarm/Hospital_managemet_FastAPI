from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.auth import decode_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not active. Awaiting admin approval.")
    return user


def require_roles(*roles: UserRole):
    """Factory: returns a dependency that restricts access to given roles."""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user
    return _check


# ── Convenience role deps ────────────────────────────────────────────────────

def admin_only(current_user: User = Depends(require_roles(UserRole.admin))) -> User:
    return current_user

def doctor_only(current_user: User = Depends(require_roles(UserRole.doctor))) -> User:
    return current_user

def receptionist_only(current_user: User = Depends(require_roles(UserRole.receptionist))) -> User:
    return current_user

def accountant_only(current_user: User = Depends(require_roles(UserRole.accountant))) -> User:
    return current_user

def admin_or_receptionist(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist))
) -> User:
    return current_user

def admin_or_doctor(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.doctor))
) -> User:
    return current_user

def staff_only(
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.doctor, UserRole.receptionist, UserRole.accountant)
    )
) -> User:
    return current_user
