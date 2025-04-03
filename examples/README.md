# Codegen PR Agent Examples

This directory contains examples of how to use the Codegen PR Agent to create pull requests with code suggestions.

## PR Suggestion Agent

The PR Suggestion Agent is a tool that can:

1. Take a user's request describing desired code changes
2. Analyze a codebase to understand its structure
3. Generate appropriate code changes
4. Create a pull request with the suggested changes

### Prerequisites

Before using the PR Agent, make sure you have:

1. Installed the Codegen SDK
2. Set up your GitHub credentials:
   - `GITHUB_TOKEN` or `GITHUB_API_KEY` environment variable
3. Set up your LLM API credentials:
   - For Anthropic: `ANTHROPIC_API_KEY`
   - For OpenAI: `OPENAI_API_KEY`

### Usage

You can use the PR Suggestion Agent in two ways:

#### 1. Command Line Interface

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"
```

Options:
- `--repo`: Repository in the format 'owner/repo' (required)
- `--request`: User request describing the desired changes (required)
- `--base-branch`: Target branch for the PR (defaults to repo's default branch)
- `--head-branch`: Source branch for the PR (defaults to a generated UUID)
- `--language`: Programming language of the codebase (default: python)
- `--model-provider`: Model provider to use (choices: anthropic, openai; default: anthropic)
- `--model-name`: Name of the model to use (default: claude-3-7-sonnet-latest)

#### 2. Python API

```python
from codegen.agents.pr_agent import create_pr_agent

# Run the PR agent
pr_info = create_pr_agent(
    repo_str="owner/repo",
    user_request="Add a new utility function to handle error logging",
    base_branch="main",  # Optional
    head_branch="feature-branch",  # Optional
    language="python",  # Optional
    model_provider="anthropic",  # Optional
    model_name="claude-3-7-sonnet-latest",  # Optional
)

# Print the result
print(pr_info["result"])
```

### Example

```bash
python pr_suggestion_agent.py --repo Perdurona/codegen --request "Add a new utility function to handle error logging in the codebase. The function should accept an error object and a context string, log the error with appropriate severity, include stack trace information, and be added to a new file called error_utils.py"
```

This will:
1. Clone the repository
2. Analyze the codebase
3. Generate the requested error logging utility function
4. Create a pull request with the changes
5. Return the PR URL and a summary of the changes

## Hardcoded Example

For a quick demonstration, you can also run the hardcoded example in the PR agent module:

```python
from codegen.agents.pr_agent import run_pr_agent_with_hardcoded_inputs

pr_info = run_pr_agent_with_hardcoded_inputs()
print(pr_info["result"])
```

This will create a PR with a predefined request on the Perdurona/codegen repository.