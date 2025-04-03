# Codegen PR Agent Examples

This directory contains examples of how to use the Codegen PR Agent to generate code changes and create pull requests based on user requests.

## PR Suggestion Agent

The PR Suggestion Agent is a command-line tool that uses Codegen's AI capabilities to:

1. Analyze a codebase
2. Generate code changes based on a user's request
3. Create a pull request with the changes

### Prerequisites

Before using the PR Suggestion Agent, make sure you have:

1. Installed the Codegen package
2. Set up your GitHub token as an environment variable or prepared to pass it as an argument
3. Access to the repository you want to modify

### Installation

```bash
# Install Codegen
pip install codegen

# Set your GitHub token as an environment variable
export GITHUB_TOKEN=your_github_token
```

### Usage

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"
```

#### Arguments

- `--repo`: Repository string in the format 'owner/repo' (required)
- `--request`: User's request describing the desired code changes (required)
- `--branch-name`: Optional name for the branch to create (defaults to a generated name)
- `--base-branch`: Optional name for the base branch (defaults to the repository's default branch)
- `--model-provider`: The model provider to use (default: anthropic, choices: anthropic, openai)
- `--model-name`: The model name to use (default: claude-3-7-sonnet-latest)
- `--github-token`: GitHub token (defaults to GITHUB_TOKEN environment variable)

### Example

```bash
python pr_suggestion_agent.py --repo fastapi/fastapi --request "Add a new utility function to handle error logging"
```

This will:
1. Clone the FastAPI repository
2. Create a new branch
3. Generate code changes to add an error logging utility function
4. Create a pull request with the changes

### Using as a Library

You can also use the PR Agent as a library in your own code:

```python
from codegen.agents.pr_agent import create_pr_agent

pr_info = create_pr_agent(
    repo_str="owner/repo",
    user_request="Add a new utility function to handle error logging",
    model_provider="anthropic",
    model_name="claude-3-7-sonnet-latest"
)

print(f"PR created: {pr_info['pr_info']['url']}")
```

## Advanced Usage

### Custom Branch Names

You can specify a custom branch name:

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Fix bug in login form" --branch-name "fix-login-bug"
```

### Using Different Base Branches

You can create PRs against branches other than the default:

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Add new feature" --base-branch "develop"
```

### Using Different Models

You can use different AI models:

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Refactor code" --model-provider "openai" --model-name "gpt-4o"
```