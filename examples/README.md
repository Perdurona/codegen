# PR Coder Agent Examples

This directory contains examples demonstrating how to use the PR Coder Agent to generate code changes and create pull requests based on natural language requests.

## PR Suggestion Agent

The `pr_suggestion_agent.py` script provides a command-line interface for the PR Coder Agent, allowing you to easily generate code changes and create pull requests from the command line.

### Usage

```bash
python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"
```

### Options

- `--repo`: Repository string in the format 'owner/repo' (required)
- `--request`: Natural language description of the code changes to implement (required)
- `--model-provider`: Model provider to use (default: anthropic, choices: anthropic, openai)
- `--model-name`: Model name to use (default: claude-3-7-sonnet-latest)
- `--no-reflection`: Disable reflection for faster but potentially lower quality results

### Example

```bash
python pr_suggestion_agent.py --repo myorg/myrepo --request "Add a new utility function to handle error logging with the following requirements:
1. Create a new file called error_logger.py in the utils directory
2. Implement a function that logs errors to both console and file
3. Add appropriate error levels (INFO, WARNING, ERROR, CRITICAL)
4. Make sure it's thread-safe
5. Add documentation and examples"
```

## Using the PR Coder Agent in Your Code

You can also use the PR Coder Agent directly in your Python code:

```python
from codegen.agents.pr_coder import create_pr_agent

# Create a PR with code changes based on a user request
result = create_pr_agent(
    repo_str="owner/repo",
    user_request="Add a new utility function to handle error logging",
    model_provider="anthropic",
    model_name="claude-3-7-sonnet-latest",
    use_reflection=True
)

# Print the result
print(result.render_as_string())

# Access PR information
if result.pr_url:
    print(f"PR created: {result.pr_url}")
    print(f"PR number: {result.pr_number}")
    print(f"PR title: {result.pr_title}")
    print(f"Files changed: {result.files_changed}")
```

## Advanced Usage

For more advanced usage, you can create a `PRCoderAgent` instance directly:

```python
from codegen import Codebase
from codegen.agents.pr_coder import PRCoderAgent

# Initialize the codebase
codebase = Codebase.from_repo("owner/repo")

# Create a unique branch for the changes
codebase.checkout(branch="feature-branch", create_if_missing=True)

# Create the PR agent
agent = PRCoderAgent(
    codebase=codebase,
    model_provider="anthropic",
    model_name="claude-3-7-sonnet-latest"
)

# Run the agent with reflection for improved results
result = agent.run_with_reflection(
    "Add a new utility function to handle error logging"
)

print(result)
```

## Features

The PR Coder Agent includes the following features:

1. **Codebase Analysis**: Analyzes the codebase to understand its structure and patterns
2. **Reflection**: Uses reflection to improve code generation quality
3. **PR Creation**: Automatically creates a pull request with the generated changes
4. **Documentation**: Generates clear PR descriptions explaining the changes
5. **Error Handling**: Provides detailed error information if PR creation fails

## Requirements

- Python 3.8+
- Codegen SDK
- GitHub access token (set as environment variable `GITHUB_TOKEN`)
- Anthropic API key (set as environment variable `ANTHROPIC_API_KEY`) or OpenAI API key (set as environment variable `OPENAI_API_KEY`)