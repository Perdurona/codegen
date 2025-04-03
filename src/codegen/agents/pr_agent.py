"""PR Agent for generating code changes and creating pull requests."""

import os
import uuid
from typing import Dict, List, Optional, Tuple, Any

from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage

from codegen import Codebase, CodeAgent
from codegen.extensions.langchain.tools import (
    GithubCreatePRTool,
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
    ViewFileTool,
    ListDirectoryTool,
    RipGrepTool,
    ReplacementEditTool,
    RelaceEditTool,
)
from codegen.agents.utils import AgentConfig


def create_pr_agent(
    repo_str: str,
    user_request: str,
    branch_name: Optional[str] = None,
    base_branch: Optional[str] = None,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-7-sonnet-latest",
    github_token: Optional[str] = None,
    additional_tools: Optional[List[BaseTool]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a PR agent that generates code changes and creates a pull request.
    
    Args:
        repo_str: Repository string in the format "owner/repo"
        user_request: User's request describing the desired code changes
        branch_name: Optional name for the branch to create (defaults to a generated name)
        base_branch: Optional name for the base branch (defaults to the repository's default branch)
        model_provider: The model provider to use (default: "anthropic")
        model_name: The model name to use (default: "claude-3-7-sonnet-latest")
        github_token: Optional GitHub token (defaults to GITHUB_TOKEN environment variable)
        additional_tools: Optional additional tools to include
        **kwargs: Additional arguments to pass to the CodeAgent
        
    Returns:
        Dictionary containing PR information (url, number, title, etc.)
    """
    # Use provided GitHub token or get from environment
    if github_token is None:
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GitHub token not provided and GITHUB_TOKEN environment variable not set")
    
    # Initialize codebase
    codebase = Codebase.from_repo(
        repo_str,
        secrets={"github_token": github_token}
    )
    
    # Generate a branch name if not provided
    if branch_name is None:
        # Create a unique branch name based on the request
        request_slug = user_request.lower().replace(" ", "-")[:20]
        unique_id = str(uuid.uuid4())[:8]
        branch_name = f"codegen-{request_slug}-{unique_id}"
    
    # Create a new branch for the changes
    if base_branch is None:
        # Get the default branch if base_branch is not specified
        default_branch = codebase._op.get_default_branch()
        base_branch = default_branch
    
    # Create and checkout the new branch
    codebase._op.create_branch(branch_name, base_branch)
    
    # Set up PR tools
    pr_tools = [
        # GitHub tools
        GithubCreatePRTool(codebase),
        GithubViewPRTool(codebase),
        GithubCreatePRCommentTool(codebase),
        GithubCreatePRReviewCommentTool(codebase),
        # Code analysis tools
        ViewFileTool(codebase),
        ListDirectoryTool(codebase),
        RipGrepTool(codebase),
        # Code editing tools
        ReplacementEditTool(codebase),
        RelaceEditTool(codebase),
    ]
    
    # Add any additional tools
    if additional_tools:
        pr_tools.extend(additional_tools)
    
    # Create the agent
    agent = CodeAgent(
        codebase=codebase,
        model_provider=model_provider,
        model_name=model_name,
        tools=pr_tools,
        **kwargs
    )
    
    # Create a prompt for the agent
    prompt = f"""
You are a PR Agent that generates code changes based on user requests and creates pull requests.

USER REQUEST: {user_request}

Follow these steps:
1. Analyze the codebase to understand its structure and patterns
2. Identify the files that need to be modified to implement the request
3. Make the necessary code changes using the editing tools
4. Create a pull request with a descriptive title and detailed description

Your PR title should be concise and descriptive.
Your PR description should explain:
- What changes were made
- Why the changes were made
- How the changes address the user's request
- Any additional context or considerations

Branch name: {branch_name}
Base branch: {base_branch}

Begin by exploring the codebase structure to understand what you're working with.
"""
    
    # Run the agent to generate changes and create PR
    result = agent.run(prompt)
    
    # Extract PR information from the result
    # This assumes the agent created a PR and included the URL in its response
    pr_info = extract_pr_info(result)
    
    return {
        "branch_name": branch_name,
        "base_branch": base_branch,
        "user_request": user_request,
        "agent_response": result,
        "pr_info": pr_info
    }


def extract_pr_info(agent_response: str) -> Dict[str, Any]:
    """Extract PR information from the agent's response.
    
    Args:
        agent_response: The agent's response text
        
    Returns:
        Dictionary containing PR information (url, number, title)
    """
    # Initialize with default values
    pr_info = {
        "url": None,
        "number": None,
        "title": None,
    }
    
    # Try to extract PR URL using regex
    import re
    
    # Look for GitHub PR URLs
    pr_url_match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/\d+', agent_response)
    if pr_url_match:
        pr_url = pr_url_match.group(0)
        pr_info["url"] = pr_url
        
        # Extract PR number from URL
        pr_number_match = re.search(r'/pull/(\d+)', pr_url)
        if pr_number_match:
            pr_info["number"] = int(pr_number_match.group(1))
    
    # Try to extract PR title
    pr_title_match = re.search(r'Pull request created: "(.*?)"', agent_response)
    if pr_title_match:
        pr_info["title"] = pr_title_match.group(1)
    
    return pr_info