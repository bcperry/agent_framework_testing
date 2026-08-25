using System.Security.Claims;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Records.Core;
using Records.Web;
using Records.Web.Components;

// Authentication lives here, in the front end, because the records API behind it has none.
// Everything the UI and the agent are allowed to read is derived from the cookie on the way in.

var builder = WebApplication.CreateBuilder(args);

DotEnv.Load(builder.Environment.ContentRootPath);
builder.Configuration.AddEnvironmentVariables();

builder.Services.AddRazorComponents().AddInteractiveServerComponents();
builder.Services.AddCascadingAuthenticationState();
builder.Services.AddAuthorization();
builder.Services
    .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.Cookie.Name = "records_demo_session";
        options.Cookie.HttpOnly = true;
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.ExpireTimeSpan = TimeSpan.FromHours(8);
        options.LoginPath = "/login";
    });

builder.Services.AddSingleton(new RecordsService(new HttpClient
{
    BaseAddress = new Uri(builder.Configuration["RECORDS_API_URL"] ?? "http://127.0.0.1:8099"),
    Timeout = TimeSpan.FromSeconds(15),
}));
builder.Services.AddSingleton<AgentFactory>();
builder.Services.AddScoped<AgentSession>();

var app = builder.Build();

app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();
app.UseAntiforgery();

// Signing in is a real form post, because setting an auth cookie needs a real HTTP response.
app.MapPost("/auth/login", async (HttpContext context, IAntiforgery antiforgery) =>
{
    await antiforgery.ValidateRequestAsync(context);

    var user = DemoDirectory.Find((await context.Request.ReadFormAsync())["upn"]);
    if (user is null)
    {
        return Results.Redirect("/login");
    }

    // Only the identifier is stored. Department, clearance and scopes are re-read from the directory
    // on every request, so nothing the browser holds can widen what the session may see.
    var identity = new ClaimsIdentity(
        new[] { new Claim(ClaimTypes.Name, user.DisplayName), new Claim("upn", user.Upn) },
        CookieAuthenticationDefaults.AuthenticationScheme);

    await context.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, new ClaimsPrincipal(identity));
    return Results.Redirect("/");
});

app.MapPost("/auth/logout", async (HttpContext context, IAntiforgery antiforgery) =>
{
    await antiforgery.ValidateRequestAsync(context);
    await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    return Results.Redirect("/login");
});

app.MapRazorComponents<App>().AddInteractiveServerRenderMode();

app.Run();
