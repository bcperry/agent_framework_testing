namespace Records.Core;

/// <summary>
/// A signed-in user. In production this comes from Entra ID: department and clearance from the
/// directory, scopes from the app registration. The demo hard-codes four of them.
/// </summary>
public sealed record DemoUser(
    string Upn,
    string DisplayName,
    string Department,
    string Clearance,
    string[] Scopes,
    string Blurb)
{
    public bool CanReadRecords => Scopes.Contains(Core.Scopes.ReadRecords);
    public bool CanReadEveryDepartment => Scopes.Contains(Core.Scopes.ReadAllRecords);
}

public static class DemoDirectory
{
    public static readonly DemoUser[] Users =
    {
        new("dana.analyst@contoso.us", "Dana Analyst", "Logistics", Clearances.Sensitive,
            new[] { Scopes.ReadRecords }, "Logistics, sensitive clearance"),

        new("ray.intern@contoso.us", "Ray Intern", "Logistics", Clearances.Unclassified,
            new[] { Scopes.ReadRecords }, "Logistics, unclassified only"),

        new("sam.auditor@contoso.us", "Sam Auditor", "*", Clearances.Restricted,
            new[] { Scopes.ReadRecords, Scopes.ReadAllRecords }, "Auditor, every department"),

        new("nia.newhire@contoso.us", "Nia Newhire", "Logistics", Clearances.Unclassified,
            new[] { "openid", "profile" }, "Signed in, but holds no records entitlement"),
    };

    public static DemoUser? Find(string? upn) =>
        Users.FirstOrDefault(u => string.Equals(u.Upn, upn, StringComparison.OrdinalIgnoreCase));
}

public static class Scopes
{
    public const string ReadRecords = "records.read";
    public const string ReadAllRecords = "records.read.all";
}

public static class Clearances
{
    public const string Unclassified = "unclassified";
    public const string Sensitive = "sensitive";
    public const string Restricted = "restricted";

    private static readonly Dictionary<string, int> Rank = new(StringComparer.OrdinalIgnoreCase)
    {
        [Unclassified] = 0,
        [Sensitive] = 1,
        [Restricted] = 2,
    };

    public static int RankOf(string? clearance) =>
        clearance is not null && Rank.TryGetValue(clearance, out var rank) ? rank : 0;
}
