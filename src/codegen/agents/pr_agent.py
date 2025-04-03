"""
PR Agent for creating pull requests with code suggestions based on user input.

This module provides a PR agent that can:
1. Take user input describing desired changes
2. Analyze a codebase
3. Generate code changes
4. Create a pull request with the suggested changes
"""

import os
from typing import Optional, List, Dict, Any

from codegen import Codebase, CodeAgent
from codegen.configs.models.secrets import SecretsConfig
from codegen.extensions.langchain.tools import (
    GithubCreatePRTool,
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
)


def create_pr_agent(
    repo_str: str,
    user_request: str,
    base_branch: Optional[str] = None,
    head_branch: Optional[str] = None,
    language: str = "python",
    model_provider: str = "anthropic",
    model_name: str = "claude-3-7-sonnet-latest",
) -> Dict[str, Any]:
    """
    Create a PR agent that generates code changes and creates a pull request.

    Args:
        repo_str: Repository string in the format "owner/repo"
        user_request: User's request describing the desired changes
        base_branch: Optional target branch for the PR (defaults to repo's default branch)
        head_branch: Optional source branch for the PR (defaults to a generated UUID)
        language: Programming language of the codebase
        model_provider: The model provider to use (e.g., "anthropic", "openai")
        model_name: Name of the model to use

    Returns:
        Dictionary containing PR information including URL and status
    """
    # Initialize codebase for the repository
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_API_KEY")
    if not github_token:
        raise ValueError("GITHUB_TOKEN or GITHUB_API_KEY environment variable must be set")

    codebase = Codebase.from_repo(
        repo_str,
        language=language,
        secrets=SecretsConfig(github_token=github_token)
    )

    # Set up PR tools
    pr_tools = [
        GithubCreatePRTool(codebase),
        GithubViewPRTool(codebase),
        GithubCreatePRCommentTool(codebase),
        GithubCreatePRReviewCommentTool(codebase),
    ]

    # Create and run the PR agent
    agent = CodeAgent(
        codebase=codebase,
        tools=pr_tools,
        model_provider=model_provider,
        model_name=model_name,
    )

    # Construct the prompt for the agent
    prompt = f"""
    I need you to create a pull request with code changes based on the following request:

    {user_request}

    Please follow these steps:
    1. Analyze the codebase to understand its structure and patterns
    2. Identify the files that need to be modified
    3. Make the necessary code changes
    4. Create a pull request with a descriptive title and detailed description
    5. The PR title should clearly indicate what changes are being made
    6. The PR description should explain the changes, the reasoning behind them, and any potential impacts

    If a base branch was specified: {base_branch if base_branch else "No base branch specified, use default"}
    If a head branch was specified: {head_branch if head_branch else "No head branch specified, generate one"}
    
    Return a summary of the changes made and the PR URL.
    """

    # Run the agent
    result = agent.run(prompt)
    
    # Extract PR information from the result
    # This is a simplified approach - in a real implementation, you might want to
    # parse the result more carefully to extract the PR URL and other details
    pr_info = {
        "result": result,
        "repo": repo_str,
        "user_request": user_request,
    }
    
    return pr_info


def run_pr_agent_with_hardcoded_inputs() -> Dict[str, Any]:
    """
    Run the PR agent with hardcoded inputs for demonstration purposes.
    
    Returns:
        Dictionary containing PR information
    """
    # Hardcoded inputs
    repo_str = "Perdurona/codegen"
    user_request = """
    Add a new utility function to handle error logging in the codebase.
    The function should:
    - Accept an error object and a context string
    - Log the error with appropriate severity
    - Include stack trace information
    - Add the function to a new file called error_utils.py
    """
    
    # Run the PR agent
    return create_pr_agent(
        repo_str=repo_str,
        user_request=user_request,
        model_provider="anthropic",
        model_name="claude-3-7-sonnet-latest",
    )


if __name__ == "__main__":
    # Example usage
    pr_info = run_pr_agent_with_hardcoded_inputs()
    print(f"PR Agent Result: {pr_info['result']}")