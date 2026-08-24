"""Minimal user-scoped REST API.

Authorization is enforced here, on every request, from the bearer token's claims.
The agent calling this API cannot widen its own access -- it can only present a
token, and this service decides what that token is worth.
"""

from fastapi import Depends, FastAPI, Header, HTTPException

from .auth import TokenError, bearer_from_header
from .data import NotAuthorized, describe_caller, get_record, visible_records

app = FastAPI(title="Records API", description="User-scoped demo API")


def caller_claims(authorization: str | None = Header(default=None)) -> dict:
    """Validate the bearer token and hand back its claims."""
    try:
        return bearer_from_header(authorization)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/me", operation_id="who_am_i")
def me(claims: dict = Depends(caller_claims)) -> dict:
    """Report the signed-in user's identity and what their permissions allow."""
    return describe_caller(claims)


@app.get("/records", operation_id="list_records")
def list_records(claims: dict = Depends(caller_claims)) -> dict:
    """List every record the signed-in user is permitted to see."""
    try:
        records = visible_records(claims)
    except NotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"count": len(records), "records": records}


@app.get("/records/{record_id}", operation_id="read_record")
def read_record(record_id: str, claims: dict = Depends(caller_claims)) -> dict:
    """Read one record by id, if the signed-in user is permitted to see it.

    Records the caller may not see return 404 rather than 403, so the response
    does not leak the existence of restricted material.
    """
    try:
        record = get_record(claims, record_id)
    except NotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"No record '{record_id}' visible to this user."
        )
    return record
