#!/usr/bin/env python
"""
PR Suggestion Agent - Command Line Interface

This script provides a command-line interface for the PR Agent, which generates
code changes based on user requests and creates pull requests.

Usage:
    python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"

Example:
    python pr_suggestion_agent.py --repo fastapi/fastapi --request "Add a new utility function to handle error logging"
"""

import argparse
import os
import sys
from typing import Optional

# Add the parent directory to the path so we can import the codegen package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codegen.agents.pr_agent import create_pr_agent


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PR Suggestion Agent - Generate code changes and create PRs based on user requests"
    )
    
    parser.add_argument(
        "--repo", 
        type=str, 
        required=True,
        help="Repository string in the format 'owner/repo'"
    )
    
    parser.add_argument(
        "--request", 
        type=str, 
        required=True,
        help="User's request describing the desired code changes"
    )
    
    parser.add_argument(
        "--branch-name", 
        type=str, 
        default=None,
        help="Optional name for the branch to create (defaults to a generated name)"
    )
    
    parser.add_argument(
        "--base-branch", 
        type=str, 
        default=None,
        help="Optional name for the base branch (defaults to the repository's default branch)"
    )
    
    parser.add_argument(
        "--model-provider", 
        type=str, 
        default="anthropic",
        choices=["anthropic", "openai"],
        help="The model provider to use (default: anthropic)"
    )
    
    parser.add_argument(
        "--model-name", 
        type=str, 
        default="claude-3-7-sonnet-latest",
        help="The model name to use (default: claude-3-7-sonnet-latest)"
    )
    
    parser.add_argument(
        "--github-token", 
        type=str, 
        default=None,
        help="GitHub token (defaults to GITHUB_TOKEN environment variable)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the PR Suggestion Agent CLI."""
    args = parse_args()
    
    # Check if GITHUB_TOKEN is set if not provided as an argument
    if args.github_token is None and "GITHUB_TOKEN" not in os.environ:
        print("Error: GitHub token not provided and GITHUB_TOKEN environment variable not set")
        print("Please set the GITHUB_TOKEN environment variable or provide it with --github-token")
        sys.exit(1)
    
    print(f"🚀 Starting PR Suggestion Agent for repository: {args.repo}")
    print(f"📝 User request: {args.request}")
    
    try:
        # Create and run the PR agent
        result = create_pr_agent(
            repo_str=args.repo,
            user_request=args.request,
            branch_name=args.branch_name,
            base_branch=args.base_branch,
            model_provider=args.model_provider,
            model_name=args.model_name,
            github_token=args.github_token,
        )
        
        # Print the results
        print("\n" + "=" * 80)
        print("✅ PR Agent completed successfully!")
        print("=" * 80)
        
        # Print PR information if available
        if result["pr_info"]["url"]:
            print(f"🔗 PR URL: {result['pr_info']['url']}")
            print(f"🔢 PR Number: {result['pr_info']['number']}")
            if result["pr_info"]["title"]:
                print(f"📋 PR Title: {result['pr_info']['title']}")
        else:
            print("⚠️ No PR was created or PR information could not be extracted from the agent's response.")
        
        print("\n📊 Additional Information:")
        print(f"🌿 Branch name: {result['branch_name']}")
        print(f"🌱 Base branch: {result['base_branch']}")
        
        # Print the agent's full response
        print("\n📜 Agent's Response:")
        print("-" * 80)
        print(result["agent_response"])
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()