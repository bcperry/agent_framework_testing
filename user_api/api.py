"""Minimal user-scoped REST API.

Authorization is enforced here, on every request, from the bearer token's claims.
The agent calling this API cannot widen its own access -- it can only present a
token, and this service decides what that token is worth.
"""

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import TokenError, decode_token
from .data import describe_caller, get_record, no_records_reason, visible_records

app = FastAPI(title="Records API", description="User-scoped demo API")

# A security scheme rather than a header parameter: it drives Swagger's Authorize
# button, and it keeps `authorization` out of the OpenAPI operation parameters --
# so the MCP tools generated from this spec have no identity argument to set.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="A demo token from user_api.auth.mint_user_token.",
)


def caller_claims(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict:
    """Validate the bearer token and hand back its claims."""
    if credentials is None:
        raise HTTPException(
            status_code=401, detail="Missing or malformed Bearer Authorization header."
        )
    try:
        return decode_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/me", operation_id="who_am_i")
def me(claims: dict = Depends(caller_claims)) -> dict:
    """Report the signed-in user's identity and what their permissions allow."""
    return describe_caller(claims)


@app.get("/records", operation_id="list_records")
def list_records(claims: dict = Depends(caller_claims)) -> dict:
    """List every record the signed-in user is permitted to see.

    A caller the token does not authorize sees zero records with a stated reason,
    not an error: the denial is data the agent can report rather than a failure it
    has to guess about. Both transports inherit the same behaviour.
    """
    records = visible_records(claims)
    body: dict = {"count": len(records), "records": records}
    if not records:
        body["reason"] = no_records_reason(claims)
    return body


@app.get("/records/{record_id}", operation_id="read_record")
def read_record(record_id: str, claims: dict = Depends(caller_claims)) -> dict:
    """Read one record by id, if the signed-in user is permitted to see it.

    Records the caller may not see return 404 rather than 403, so the response
    does not leak the existence of restricted material.
    """
    record = get_record(claims, record_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"No record '{record_id}' visible to this user."
        )
    return record
