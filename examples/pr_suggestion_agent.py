#!/usr/bin/env python3
"""
PR Suggestion Agent - Command Line Interface

This script provides a command-line interface for the PR Coder Agent,
allowing users to generate code changes and create pull requests based
on natural language requests.

Example usage:
    python pr_suggestion_agent.py --repo owner/repo --request "Add error logging utility"
"""

import argparse
import sys
from typing import Optional

from codegen.agents.pr_coder import create_pr_agent, PRCoderObservation


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate code changes and create a pull request based on a natural language request"
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
        help="Natural language description of the code changes to implement"
    )
    parser.add_argument(
        "--model-provider", 
        type=str, 
        default="anthropic", 
        choices=["anthropic", "openai"],
        help="Model provider to use (default: anthropic)"
    )
    parser.add_argument(
        "--model-name", 
        type=str, 
        default="claude-3-7-sonnet-latest", 
        help="Model name to use (default: claude-3-7-sonnet-latest)"
    )
    parser.add_argument(
        "--no-reflection", 
        action="store_true", 
        help="Disable reflection for faster but potentially lower quality results"
    )
    
    return parser.parse_args()


def main():
    """Run the PR Suggestion Agent with command line arguments."""
    args = parse_args()
    
    print(f"Generating PR for repository: {args.repo}")
    print(f"Request: {args.request}")
    print(f"Using model: {args.model_provider}/{args.model_name}")
    print(f"Reflection enabled: {not args.no_reflection}")
    print("-" * 80)
    
    try:
        result = create_pr_agent(
            repo_str=args.repo,
            user_request=args.request,
            model_provider=args.model_provider,
            model_name=args.model_name,
            use_reflection=not args.no_reflection
        )
        
        print("\n" + "=" * 80)
        print(result.render_as_string())
        print("=" * 80)
        
        if result.status == "error":
            sys.exit(1)
        
        # Return PR URL if available
        if result.pr_url:
            print(f"\nPR created successfully: {result.pr_url}")
        else:
            print("\nPR creation pending or failed. See summary for details.")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()