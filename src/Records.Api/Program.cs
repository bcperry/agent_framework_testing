// The customer's back end, modelled honestly: no authentication, no authorization, no identity on
// the wire. Anyone who can reach this port gets every row. Scoping is therefore not something this
// service can do -- it has to happen in the agent host, the only tier that knows who the user is.
// See src/Records.Core/AccessPolicy.cs.

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var records = new[]
{
    new Record("REC-001", "Q3 fleet fuel consumption", "Logistics", "unclassified",
        "Routine fuel burn across the regional truck fleet, up 4% quarter over quarter."),
    new Record("REC-002", "Cold-chain shipment failures", "Logistics", "sensitive",
        "Three refrigerated shipments breached temperature thresholds in transit to Site B."),
    new Record("REC-003", "Vendor contract renegotiation", "Logistics", "restricted",
        "Draft terms reducing per-mile rate by 11% pending legal review. Not for wide release."),
    new Record("REC-004", "Payroll variance review", "Finance", "sensitive",
        "Overtime spend exceeded forecast in two cost centers."),
    new Record("REC-005", "Benefits enrollment summary", "Finance", "unclassified",
        "Open enrollment participation reached 87% of eligible staff."),
};

app.MapGet("/", () => Results.Text(
    $"Records API. No authentication. GET /records returns all {records.Length} rows to any caller.",
    "text/plain"));

app.MapGet("/records", () => Results.Json(records));

app.MapGet("/records/{id}", (string id) =>
{
    var match = records.FirstOrDefault(r => string.Equals(r.Id, id, StringComparison.OrdinalIgnoreCase));
    return match is null ? Results.NotFound() : Results.Json(match);
});

app.Run();

record Record(string Id, string Title, string Department, string Classification, string Summary);
