using Microsoft.Agents.AI;
using Records.Core;

namespace Records.Web;

internal sealed class Message
{
    public string Role { get; set; } = "user";
    public string Text { get; set; } = "";
}

/// <summary>
/// One agent and one conversation per signed-in browser session (scoped = per Blazor circuit).
/// The agent is not shared, because its tools are bound to a single user.
/// </summary>
internal sealed class AgentSession
{
    private readonly AgentFactory _factory;
    private AIAgent? _agent;

    public AgentSession(AgentFactory factory) => _factory = factory;

    public DemoUser? User { get; private set; }
    public List<Message> Messages { get; } = new();
    public bool IsBusy { get; private set; }

    public void Start(DemoUser user)
    {
        if (_agent is not null)
        {
            return;
        }

        User = user;
        _agent = _factory.CreateAgent(user);
    }

    public void Restart() => Messages.Clear();

    public async Task SendAsync(string message, Func<Task> render, CancellationToken cancellationToken = default)
    {
        if (_agent is null || IsBusy || string.IsNullOrWhiteSpace(message))
        {
            return;
        }

        IsBusy = true;
        Messages.Add(new Message { Role = "user", Text = message });

        var reply = new Message { Role = "agent" };
        Messages.Add(reply);
        await render();

        try
        {
            await foreach (var update in _agent.RunStreamingAsync(message, session: null, cancellationToken: cancellationToken))
            {
                if (string.IsNullOrEmpty(update.Text))
                {
                    continue;
                }

                reply.Text += update.Text;
                await render();
            }
        }
        catch (Exception ex)
        {
            reply.Role = "error";
            reply.Text = ex.Message;
        }
        finally
        {
            IsBusy = false;
            await render();
        }
    }
}
