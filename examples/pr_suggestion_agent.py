#!/usr/bin/env python
"""
PR Suggestion Agent - Command Line Interface

This script provides a command-line interface for the PR Coder Agent,
allowing users to generate code changes and create pull requests based on
natural language requests.

Usage:
    python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"

Options:
    --repo          Repository string in the format "owner/repo"
    --request       The user's request describing the desired code changes
    --branch        Optional name for the branch to create
    --base          Optional name for the base branch
    --model         Model name to use (default: claude-3-7-sonnet-latest)
    --provider      Model provider to use (default: anthropic)
    --token         GitHub token (if not provided, will use GITHUB_TOKEN env var)
"""

import argparse
import os
import sys
from typing import Optional

# Add the parent directory to the path so we can import the codegen module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from codegen import Codebase
    from codegen.agents.pr_coder import create_pr_agent
    from codegen.secrets import SecretsConfig
except ImportError:
    print("Error: Could not import codegen modules. Make sure the codegen package is installed.")
    sys.exit(1)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PR Suggestion Agent")
    
    parser.add_argument(
        "--repo", 
        required=True,
        help="Repository string in the format 'owner/repo'"
    )
    
    parser.add_argument(
        "--request", 
        required=True,
        help="The user's request describing the desired code changes"
    )
    
    parser.add_argument(
        "--branch", 
        default=None,
        help="Optional name for the branch to create"
    )
    
    parser.add_argument(
        "--base", 
        default=None,
        help="Optional name for the base branch"
    )
    
    parser.add_argument(
        "--model", 
        default="claude-3-7-sonnet-latest",
        help="Model name to use (default: claude-3-7-sonnet-latest)"
    )
    
    parser.add_argument(
        "--provider", 
        default="anthropic",
        help="Model provider to use (default: anthropic)"
    )
    
    parser.add_argument(
        "--token", 
        default=None,
        help="GitHub token (if not provided, will use GITHUB_TOKEN env var)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the PR Suggestion Agent CLI."""
    args = parse_args()
    
    # Check for GitHub token
    github_token = args.token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GitHub token not provided. Please provide a token with --token or set the GITHUB_TOKEN environment variable.")
        sys.exit(1)
    
    print(f"Generating PR for repository: {args.repo}")
    print(f"Request: {args.request}")
    print(f"Using model: {args.provider}/{args.model}")
    
    try:
        # Create PR agent and generate PR
        pr_info = create_pr_agent(
            repo_str=args.repo,
            user_request=args.request,
            branch_name=args.branch,
            base_branch=args.base,
            model_provider=args.provider,
            model_name=args.model,
            github_token=github_token,
        )
        
        print("\n" + "=" * 80)
        print("PR GENERATION COMPLETED")
        print("=" * 80)
        print(f"Branch: {pr_info.get('branch_name')}")
        print(f"Base branch: {pr_info.get('base_branch') or 'default'}")
        
        # Print the agent's response
        print("\nAgent Response:")
        print("-" * 80)
        print(pr_info.get("agent_response", "No response provided"))
        
    except Exception as e:
        print(f"Error generating PR: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()