# Codegen PR Agent Examples

This directory contains examples of how to use the Codegen PR Agent to generate code changes and create pull requests based on natural language requests.

## PR Suggestion Agent

The PR Suggestion Agent is a command-line tool that allows you to generate code changes and create pull requests based on natural language requests.

### Usage

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"
```

### Options

- `--repo`: Repository string in the format "owner/repo"
- `--request`: The user's request describing the desired code changes
- `--branch`: Optional name for the branch to create
- `--base`: Optional name for the base branch
- `--model`: Model name to use (default: claude-3-7-sonnet-latest)
- `--provider`: Model provider to use (default: anthropic)
- `--token`: GitHub token (if not provided, will use GITHUB_TOKEN env var)

### Example

```bash
python pr_suggestion_agent.py \
  --repo "Perdurona/codegen" \
  --request "Add a new utility function to handle error logging" \
  --model "claude-3-7-sonnet-latest" \
  --provider "anthropic"
```

## Using the PR Agent in Your Code

You can also use the PR Agent directly in your Python code:

```python
from codegen.agents.pr_coder import create_pr_agent

# Create PR agent and generate PR
pr_info = create_pr_agent(
    repo_str="owner/repo",
    user_request="Add a new utility function to handle error logging",
    branch_name="feature-error-logging",  # Optional
    base_branch="main",  # Optional
    model_provider="anthropic",  # Optional
    model_name="claude-3-7-sonnet-latest",  # Optional
    github_token="your_github_token",  # Optional, will use GITHUB_TOKEN env var if not provided
)

# Access PR information
print(f"PR created with branch: {pr_info.get('branch_name')}")
print(f"Agent response: {pr_info.get('agent_response')}")
```

## How It Works

The PR Agent works by:

1. Analyzing the codebase to understand its structure and the relevant components
2. Identifying the files that need to be modified or created
3. Making the necessary code changes to implement the request
4. Creating a pull request with a descriptive title and detailed description

The agent uses a combination of code analysis tools, code modification tools, and GitHub PR tools to accomplish these tasks.

## Requirements

- Python 3.8+
- Codegen SDK
- GitHub token with appropriate permissions
- API key for the chosen model provider (Anthropic or OpenAI)

## Environment Variables

The following environment variables can be set:

- `GITHUB_TOKEN`: GitHub token with appropriate permissions
- `ANTHROPIC_API_KEY`: Anthropic API key (if using Anthropic models)
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI models)
- `LANGCHAIN_PROJECT`: LangSmith project name (optional, for tracing)