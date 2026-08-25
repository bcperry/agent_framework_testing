"""Demo dataset and the authorization rules applied to it.

Every access decision here is made from **token claims**, server-side. The agent
and the model never get a say in what the caller is allowed to see -- that is the
whole point of the demo.
"""

# Demo identities. In production these are just Entra users; roles/scopes come
# from app role assignments and delegated permissions on the app registration.
DEMO_USERS: dict[str, dict] = {
    "dana.analyst@contoso.us": {
        "oid": "11111111-1111-1111-1111-111111111111",
        "upn": "dana.analyst@contoso.us",
        "name": "Dana Analyst",
        "department": "Logistics",
        "clearance": "sensitive",
        "roles": ["Records.Reader"],
        "scp": "records.read",
    },
    "ray.intern@contoso.us": {
        "oid": "22222222-2222-2222-2222-222222222222",
        "upn": "ray.intern@contoso.us",
        "name": "Ray Intern",
        "department": "Logistics",
        "clearance": "unclassified",
        "roles": ["Records.Reader"],
        "scp": "records.read",
    },
    "sam.auditor@contoso.us": {
        "oid": "33333333-3333-3333-3333-333333333333",
        "upn": "sam.auditor@contoso.us",
        "name": "Sam Auditor",
        "department": "*",
        "clearance": "restricted",
        "roles": ["Records.Reader", "Records.Auditor"],
        "scp": "records.read records.read.all",
    },
    "nia.newhire@contoso.us": {
        "oid": "44444444-4444-4444-4444-444444444444",
        "upn": "nia.newhire@contoso.us",
        "name": "Nia Newhire",
        "department": "Logistics",
        "clearance": "unclassified",
        "roles": [],
        "scp": "openid profile",  # authenticated, but not authorized for records
    },
}

CLEARANCE_ORDER = {"unclassified": 0, "sensitive": 1, "restricted": 2}

RECORDS: list[dict] = [
    {
        "id": "REC-001",
        "title": "Q3 fleet fuel consumption",
        "department": "Logistics",
        "classification": "unclassified",
        "summary": "Routine fuel burn across the regional truck fleet, up 4% quarter over quarter.",
    },
    {
        "id": "REC-002",
        "title": "Cold-chain shipment failures",
        "department": "Logistics",
        "classification": "sensitive",
        "summary": "Three refrigerated shipments breached temperature thresholds in transit to Site B.",
    },
    {
        "id": "REC-003",
        "title": "Vendor contract renegotiation",
        "department": "Logistics",
        "classification": "restricted",
        "summary": "Draft terms reducing per-mile rate by 11% pending legal review. Not for wide release.",
    },
    {
        "id": "REC-004",
        "title": "Payroll variance review",
        "department": "Finance",
        "classification": "sensitive",
        "summary": "Overtime spend exceeded forecast in two cost centers.",
    },
    {
        "id": "REC-005",
        "title": "Benefits enrollment summary",
        "department": "Finance",
        "classification": "unclassified",
        "summary": "Open enrollment participation reached 87% of eligible staff.",
    },
]


def _scopes(claims: dict) -> set[str]:
    return set(claims.get("scp", "").split())


def describe_caller(claims: dict) -> dict:
    """Summarize who the caller is and what their token actually permits."""
    upn = claims.get("upn", "")
    profile = DEMO_USERS.get(upn, {})
    scopes = _scopes(claims)
    return {
        "upn": upn,
        "name": claims.get("name"),
        "oid": claims.get("oid"),
        "roles": claims.get("roles", []),
        "scopes": sorted(scopes),
        "department": profile.get("department", "unknown"),
        "clearance": profile.get("clearance", "unclassified"),
        "can_read_records": "records.read" in scopes,
        "can_read_all_departments": "records.read.all" in scopes,
    }


def visible_records(claims: dict) -> list[dict]:
    """Return only the records this caller's claims permit -- possibly none."""
    scopes = _scopes(claims)
    if "records.read" not in scopes:
        return []

    profile = DEMO_USERS.get(claims.get("upn", ""), {})
    department = profile.get("department", "")
    ceiling = CLEARANCE_ORDER.get(profile.get("clearance", "unclassified"), 0)
    all_departments = "records.read.all" in scopes

    return [
        record
        for record in RECORDS
        if (all_departments or record["department"] == department)
        and CLEARANCE_ORDER[record["classification"]] <= ceiling
    ]


def no_records_reason(claims: dict) -> str:
    """Explain an empty result, so an agent can report it instead of guessing."""
    if "records.read" not in _scopes(claims):
        return (
            "Token lacks the 'records.read' scope: the signed-in user is authenticated "
            "but not authorized to read records."
        )
    return "No records match this user's department and clearance."


def get_record(claims: dict, record_id: str) -> dict | None:
    """Fetch one record, or None if it does not exist *or* the caller may not see it."""
    wanted = record_id.strip().upper()
    return next((r for r in visible_records(claims) if r["id"] == wanted), None)
