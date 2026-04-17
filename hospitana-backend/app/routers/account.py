from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.permissions import get_current_user, accountant_only

router = APIRouter(prefix="/account", tags=["Account"])


# ── Accountant dashboard ──────────────────────────────────────────────────────

@router.get("/dashboard")
def account_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(accountant_only),
):
    """
    Phase 1 stub — billing data will be added in next phase.
    Returns basic user counts for now.
    """
    total_patients = db.query(User).filter(User.role == UserRole.patient).count()

    return {
        "accountant": f"{current_user.first_name} {current_user.last_name}",
        "message": "Billing module coming in Phase 2",
        "total_patients": total_patients,
        # billing stats will go here
        "total_revenue":    0,
        "pending_payments": 0,
        "today_collection": 0,
    }


# ── Profile (accountant sees own info) ───────────────────────────────────────

@router.get("/profile")
def account_profile(current_user: User = Depends(accountant_only)):
    return {
        "id":         current_user.id,
        "name":       f"{current_user.first_name} {current_user.last_name}",
        "email":      current_user.email,
        "phone":      current_user.phone,
        "role":       current_user.role.value,
        "is_active":  current_user.is_active,
    }
