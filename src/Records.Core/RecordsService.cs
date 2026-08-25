using System.Net.Http;
using System.Text.Json;

namespace Records.Core;

/// <summary>
/// The application's one read path for records. The Blazor page calls it to render the user's list;
/// the agent's tools call the same two methods. Authorization is applied here, once, so both callers
/// get identical results and there is no second place for the rules to drift.
///
/// The records API behind this service has no authentication -- it returns every row to any caller --
/// so this is where entitlements are enforced.
/// </summary>
public sealed class RecordsService
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    private readonly HttpClient _http;

    public RecordsService(HttpClient http) => _http = http;

    /// <summary>Every record <paramref name="user"/> is entitled to see.</summary>
    public async Task<IReadOnlyList<RecordItem>> ListAsync(DemoUser user, CancellationToken cancellationToken = default)
    {
        if (!user.CanReadRecords)
        {
            return Array.Empty<RecordItem>();
        }

        var ceiling = Clearances.RankOf(user.Clearance);

        var all = await ListEverythingAsync(cancellationToken).ConfigureAwait(false);

        return all.Where(record =>
                (user.CanReadEveryDepartment ||
                 string.Equals(record.Department, user.Department, StringComparison.OrdinalIgnoreCase))
                && Clearances.RankOf(record.Classification) <= ceiling)
            .ToList();
    }

    /// <summary>One record by id, or null if it does not exist or <paramref name="user"/> may not see it.</summary>
    public async Task<RecordItem?> GetAsync(DemoUser user, string id, CancellationToken cancellationToken = default)
    {
        var visible = await ListAsync(user, cancellationToken).ConfigureAwait(false);
        return visible.FirstOrDefault(r => string.Equals(r.Id, id?.Trim(), StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>What the unauthenticated API hands to anybody. Shown in the UI only for contrast.</summary>
    public async Task<IReadOnlyList<RecordItem>> ListEverythingAsync(CancellationToken cancellationToken = default)
    {
        using var response = await _http.GetAsync("/records", cancellationToken).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();

        var body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        return JsonSerializer.Deserialize<List<RecordItem>>(body, Json) ?? new List<RecordItem>();
    }
}
