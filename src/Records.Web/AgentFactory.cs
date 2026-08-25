using System.ClientModel;
using Azure.AI.OpenAI;
using Azure.Identity;
using Microsoft.Agents.AI;
using OpenAI.Chat;
using Records.Core;

namespace Records.Web;

/// <summary>Azure OpenAI wiring, including Azure Government, and one agent per signed-in user.</summary>
internal sealed class AgentFactory
{
    private const string GovernmentEndpointSuffix = ".azure.us";

    private readonly ChatClient _chatClient;
    private readonly RecordsService _records;

    public AgentFactory(IConfiguration configuration, RecordsService records)
    {
        _records = records;

        var endpoint = configuration["AZURE_OPENAI_ENDPOINT"]
            ?? throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT is not set. Copy .env.example to .env and fill it in.");
        var deployment = configuration["AZURE_OPENAI_MODEL"]
            ?? throw new InvalidOperationException("AZURE_OPENAI_MODEL is not set. Copy .env.example to .env and fill it in.");
        var apiKey = configuration["AZURE_OPENAI_API_KEY"];

        var uri = new Uri(endpoint);
        var isGovernment = uri.Host.EndsWith(GovernmentEndpointSuffix, StringComparison.OrdinalIgnoreCase);

        var options = new AzureOpenAIClientOptions();
        if (isGovernment)
        {
            options.Audience = AzureOpenAIAudience.AzureGovernment;
        }

        var client = string.IsNullOrWhiteSpace(apiKey)
            ? new AzureOpenAIClient(uri, CredentialFor(isGovernment), options)
            : new AzureOpenAIClient(uri, new ApiKeyCredential(apiKey), options);

        _chatClient = client.GetChatClient(deployment);
    }

    private static DefaultAzureCredential CredentialFor(bool isGovernment) =>
        new(new DefaultAzureCredentialOptions
        {
            AuthorityHost = isGovernment
                ? AzureAuthorityHosts.AzureGovernment
                : AzureAuthorityHosts.AzurePublicCloud,
        });

    /// <summary>An agent whose tools are bound to this user, and to nobody else.</summary>
    public AIAgent CreateAgent(DemoUser user) => _chatClient.AsAIAgent(
        instructions: RecordTools.Instructions,
        name: "RecordsAgent",
        tools: RecordTools.For(user, _records));
}
