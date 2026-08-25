# User-scoped agent tools — .NET demo

An agent that can only see what the signed-in user can see, in a system where **the back-end API has
no authentication at all** and authorization lives in the front end.

The whole demo is one sentence: **the agent's tools are a thin wrapper around the same method the UI
already calls.** No second data path, no second copy of the rules, no new trust boundary.

```csharp
// The page renders the user's list with this:
_visible = await Records.ListAsync(user);

// The agent's tool is this:
AIFunctionFactory.Create(
    (CancellationToken ct) => records.ListAsync(user, ct),
    "list_records",
    "List the records the signed-in user is allowed to see.");
```

`user` is captured from the browser session when the tools are built. It is not a tool parameter, so
it never appears in the schema the model sees: the model decides *whether* to call a tool, never
*who as*.

---

## Layout

| Project | Target | Role |
|---|---|---|
| [src/Records.Api](src/Records.Api) | net8.0 | The back end, modelled honestly — no auth, hands all five records to anyone |
| [src/Records.Core](src/Records.Core) | netstandard2.0, net8.0 | [`RecordsService`](src/Records.Core/RecordsService.cs), the one authorized read path, and [`RecordTools`](src/Records.Core/RecordTools.cs), the wrapper |
| [src/Records.Web](src/Records.Web) | net8.0 | Blazor Server: cookie sign-in, the records page, and the agent |

`Records.Core` also targets **netstandard2.0**, so the same service and tool code drops into a .NET
Framework 4.8 application unchanged.

## Prerequisites

- .NET 8 SDK
- An Azure OpenAI resource with a deployed model (Azure Government included)
- `az login`, unless you set an API key

## Setup

```bash
cp .env.example .env    # then fill it in
```

```bash
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_MODEL=<your-deployment-name>
AZURE_OPENAI_API_KEY=<optional; omit to use Entra ID>
```

An endpoint ending in `.azure.us` switches both the credential authority and the token audience to
Azure Government automatically.

## Run

Press **Ctrl+Shift+B**, or use two terminals:

```bash
$HOME/.dotnet-local/dotnet run --project src/Records.Api    # http://127.0.0.1:8099
$HOME/.dotnet-local/dotnet run --project src/Records.Web    # http://localhost:8080
```

This WSL installation has its SDK and runtime in different system directories, so `/usr/bin/dotnet`
cannot find the runtime. The VS Code tasks and commands above use the unified user-local install.

Open <http://localhost:8080>, sign in as one of the four users, and ask the agent what it can see.
Sign out, sign in as somebody else, ask the identical question.

## The users

Records are filtered by department and clearance. Same agent, same prompt, same model — only the
signed-in user differs.

| User | Department | Clearance | Scopes | Sees |
|---|---|---|---|---|
| Dana Analyst | Logistics | sensitive | `records.read` | 2 records |
| Ray Intern | Logistics | unclassified | `records.read` | 1 record |
| Sam Auditor | all | restricted | `records.read`, `records.read.all` | 5 records |
| Nia Newhire | Logistics | unclassified | `openid`, `profile` | **nothing** — signed in, not entitled |

The records list and the agent always agree, because both go through `RecordsService.ListAsync(user)`.

## The tool wrapper in detail

The agent does not have a separate permission system or a privileged data client. It receives the
same `DemoUser` that the rest of the web application uses and calls the same `RecordsService`
methods that the records page calls. Adding the agent changes the interface used to request data;
it does not change how data is retrieved or authorized.

### The normal web application path

After cookie authentication, the Blazor page resolves the signed-in user from the directory. That
`DemoUser` contains the user's department, clearance and scopes. The page retrieves its records by
passing that user to the application's normal data service:

```csharp
_visible = await Records.ListAsync(_user);
```

`RecordsService.ListAsync(user)` calls the unauthenticated records API, then applies the user's
existing permissions. It requires the `records.read` scope, limits results to the user's department
unless the user has `records.read.all`, and excludes records above the user's clearance. The page
never filters records itself; it renders only what the service returns.

Reading one record follows the same rule. `RecordsService.GetAsync(user, id)` searches the result of
`ListAsync(user)`, so requesting a known id cannot bypass the list authorization. A record that does
not exist and a record the user cannot access both return `null`.

### The agent path

When an agent session starts, `RecordTools.For(user, records)` receives that same signed-in
`DemoUser` and the same `RecordsService` instance. Its two data tools are direct adapters:

```csharp
AIFunctionFactory.Create(
  (CancellationToken cancellationToken) => records.ListAsync(user, cancellationToken),
  "list_records",
  "List the records the signed-in user is allowed to see.");

AIFunctionFactory.Create(
  (string id, CancellationToken cancellationToken) =>
    records.GetAsync(user, id, cancellationToken),
  "read_record",
  "Read one record by id. Returns nothing if the signed-in user is not allowed to see it.");
```

The wrapper adds only the function names and descriptions needed by the model. It does not fetch
data directly, duplicate the department or clearance rules, or grant the agent additional access.
For example, these two actions are authorization-equivalent:

```csharp
// User asks the web page to display their records.
await records.ListAsync(user);

// User asks the agent, and its tool invokes the same operation.
await records.ListAsync(user, cancellationToken);
```

The model sees an optional record id for `read_record`, but it never sees a user, department,
clearance or scope argument. Those values are captured in the tool delegates when the session is
created. Therefore the model can choose which available operation to invoke, but it cannot replace
the signed-in user, manufacture broader permissions, or ask the service to skip authorization.

This is the important boundary: the agent is another caller of the web application's existing,
user-scoped data access methods. It has no more authority than the signed-in user clicking through
the non-agent records interface. If permission behavior changes, it changes once in
`RecordsService`, and both the page and agent immediately receive the same result.

## Why the model cannot escalate

- **The API has no auth, so the front end is the trust boundary.** `RecordsService` applies
  entitlements once, and the page and the tools both go through it.
- **Identity comes from the cookie, not the conversation.** The cookie carries only a user
  identifier; department, clearance and scopes are re-read from the directory on every request.
- **There is no identity parameter.** The tools take a record id and nothing else, so a prompt
  injection has nothing to aim at. The chat page has a button that tries one.

## Moving to real identity

Swap the demo sign-in for Entra ID (`AddMicrosoftIdentityWebApp`) and build `DemoUser` from the
signed-in principal's claims instead of `DemoDirectory`. Nothing downstream changes — neither
`RecordsService` nor `RecordTools` knows where the user object came from.

If the API later gains authentication, move the filtering into it and let `RecordsService` forward
the user's token. The tool wrapper stays exactly as it is.
