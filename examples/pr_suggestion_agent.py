#!/usr/bin/env python3
"""
Example script demonstrating how to use the PR Agent to create pull requests with code suggestions.

This script shows how to:
1. Set up the PR agent with a repository and user request
2. Run the agent to generate code changes and create a PR
3. Handle the results

Usage:
    python pr_suggestion_agent.py --repo owner/repo --request "Your feature request here"
"""

import argparse
import os
import sys
from typing import Dict, Any

# Add the parent directory to the path so we can import the codegen module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codegen.agents.pr_agent import create_pr_agent


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create a PR with code suggestions based on a user request"
    )
    parser.add_argument(
        "--repo", 
        type=str, 
        required=True,
        help="Repository in the format 'owner/repo'"
    )
    parser.add_argument(
        "--request", 
        type=str, 
        required=True,
        help="User request describing the desired changes"
    )
    parser.add_argument(
        "--base-branch", 
        type=str, 
        default=None,
        help="Target branch for the PR (defaults to repo's default branch)"
    )
    parser.add_argument(
        "--head-branch", 
        type=str, 
        default=None,
        help="Source branch for the PR (defaults to a generated UUID)"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default="python",
        help="Programming language of the codebase"
    )
    parser.add_argument(
        "--model-provider", 
        type=str, 
        default="anthropic",
        choices=["anthropic", "openai"],
        help="Model provider to use"
    )
    parser.add_argument(
        "--model-name", 
        type=str, 
        default="claude-3-7-sonnet-latest",
        help="Name of the model to use"
    )
    
    return parser.parse_args()


def run_pr_agent(args) -> Dict[str, Any]:
    """Run the PR agent with the provided arguments."""
    print(f"Creating PR agent for repository: {args.repo}")
    print(f"User request: {args.request}")
    
    # Check for required environment variables
    if not (os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_API_KEY")):
        print("Error: GITHUB_TOKEN or GITHUB_API_KEY environment variable must be set")
        sys.exit(1)
        
    # Run the PR agent
    try:
        pr_info = create_pr_agent(
            repo_str=args.repo,
            user_request=args.request,
            base_branch=args.base_branch,
            head_branch=args.head_branch,
            language=args.language,
            model_provider=args.model_provider,
            model_name=args.model_name,
        )
        return pr_info
    except Exception as e:
        print(f"Error creating PR: {e}")
        sys.exit(1)


def main():
    """Main function to run the PR agent."""
    args = parse_arguments()
    
    print("Starting PR Agent...")
    pr_info = run_pr_agent(args)
    
    print("\n" + "="*50)
    print("PR Agent completed successfully!")
    print("="*50)
    print(f"Result: {pr_info['result']}")
    print("="*50)


if __name__ == "__main__":
    main()