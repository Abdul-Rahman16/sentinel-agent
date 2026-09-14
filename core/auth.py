from fastapi import Header, HTTPException

from core.config import settings


def get_current_user_id(
    x_internal_secret: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str | None:
    """
    Returns the verified user id, or None for an anonymous/demo request.
    Trust boundary: we only believe X-User-Id if it arrives alongside the
    correct shared secret — proving the request came from our own Next.js
    server (which already verified the real session), not directly from
    a browser that could fake any header it wants.
    """
    if x_user_id is None:
        return None  # anonymous demo request — always allowed

    if not settings.internal_api_secret or x_internal_secret != settings.internal_api_secret:
        raise HTTPException(status_code=401, detail="Invalid internal secret for authenticated request")

    return x_user_id