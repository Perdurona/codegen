#!/usr/bin/env python
"""
PR Generation CLI Tool

This script provides an interactive command-line interface for generating pull requests
using the PR Generation System.
"""

import os
import sys
import getpass
import argparse
from typing import Dict, Any, Optional, Tuple

# Import from the integrated system
try:
    from .pr_coder import PRCoderAgent, create_pr_agent
    from .config import PRGenerationConfig
    from .utils.logging import get_logger
except ImportError:
    # Allow script to be run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pr_generation.pr_coder import PRCoderAgent, create_pr_agent
    from pr_generation.config import PRGenerationConfig
    from pr_generation.utils.logging import get_logger

# Import required codegen modules
try:
    from codegen import Codebase
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure the codegen package is installed correctly.")
    sys.exit(1)

# Set up logger
logger = get_logger(__name__)

def get_github_token() -> str:
    """Get GitHub token from environment or prompt user."""
    token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("\nGitHub token not found in environment variables.")
        token = getpass.getpass("Please enter your GitHub token: ")
        
        if not token:
            print("Error: GitHub token is required to create PRs.")
            sys.exit(1)
            
        # Save to environment for current session
        os.environ["GITHUB_TOKEN"] = token
        
    return token


def select_project_source() -> Tuple[str, str]:
    """
    Prompt user to select project source type and location.
    
    Returns:
        Tuple containing (source_type, location)
    """
    print("\n=== Project Selection ===")
    print("1. GitHub repository")
    print("2. Local project")
    
    while True:
        choice = input("\nSelect project source type (1-2): ").strip()
        
        if choice == "1":
            # GitHub repository
            repo = input("Enter GitHub repository (format: owner/repo): ").strip()
            if "/" not in repo:
                print("Error: Invalid repository format. Please use 'owner/repo' format.")
                continue
            return "github", repo
            
        elif choice == "2":
            # Local project
            path = input("Enter local project path: ").strip()
            if not os.path.isdir(path):
                print(f"Error: Directory '{path}' does not exist.")
                continue
            return "local", os.path.abspath(path)
            
        else:
            print("Invalid choice. Please select 1 or 2.")


def get_requirements() -> str:
    """Get detailed requirements from user."""
    print("\n=== Requirements ===")
    print("Describe the changes you want to make to the project.")
    print("Be as specific as possible about what you want to implement or modify.")
    print("Enter your requirements below (type 'END' on a new line when finished):\n")
    
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    
    return "\n".join(lines)


def get_optional_parameters() -> Dict[str, Any]:
    """Get optional parameters for PR generation."""
    params = {}
    
    print("\n=== Optional Parameters ===")
    print("Press Enter to use default values.")
    
    # Branch name
    branch = input("Branch name (default: auto-generated): ").strip()
    if branch:
        params["branch_name"] = branch
    
    # Base branch
    base = input("Base branch (default: main/master): ").strip()
    if base:
        params["base_branch"] = base
    
    # Model settings
    print("\n=== Model Settings ===")
    
    # Model provider
    print("Available model providers:")
    print("1. Anthropic (default)")
    print("2. OpenAI")
    
    provider_choice = input("Select model provider (1-2): ").strip()
    if provider_choice == "2":
        params["model_provider"] = "openai"
    else:
        params["model_provider"] = "anthropic"
    
    # Model name
    if params["model_provider"] == "anthropic":
        default_model = "claude-3-7-sonnet-latest"
    else:
        default_model = "gpt-4o"
        
    model = input(f"Model name (default: {default_model}): ").strip()
    if model:
        params["model_name"] = model
    else:
        params["model_name"] = default_model
    
    # Reflection
    use_reflection = input("Use reflection for better results? This increases processing time. (Y/n): ").strip().lower()
    params["use_reflection"] = use_reflection != "n"
    
    return params


def process_github_project(repo: str, requirements: str, params: Dict[str, Any]) -> None:
    """Process a GitHub project to generate PR."""
    print(f"\nProcessing GitHub repository: {repo}")
    
    # Set the GitHub token
    github_token = get_github_token()
    
    try:
        # Use the create_pr_agent function
        result = create_pr_agent(
            repo_str=repo,
            user_request=requirements,
            branch_name=params.get("branch_name"),
            base_branch=params.get("base_branch"),
            model_provider=params.get("model_provider", "anthropic"),
            model_name=params.get("model_name", "claude-3-7-sonnet-latest"),
            use_reflection=params.get("use_reflection", True),
            github_token=github_token
        )
        
        # Display the result
        print("\nPR Generation Result:")
        print("=" * 80)
        
        if hasattr(result, "render_as_string"):
            # It's a structured object like PRCoderObservation
            print(result.render_as_string())
        elif isinstance(result, dict):
            # It's a dictionary
            print(f"Branch: {result.get('branch_name')}")
            print(f"Base branch: {result.get('base_branch') or 'default'}")
            print("\nAgent Response:")
            print("-" * 80)
            print(result.get("agent_response", "No response provided"))
        else:
            # It's something else (like a string)
            print(result)
        
    except Exception as e:
        print(f"Error processing GitHub repository: {e}")
        logger.error(f"Error processing GitHub repository: {e}", exc_info=True)
        sys.exit(1)


def process_local_project(path: str, requirements: str, params: Dict[str, Any]) -> None:
    """Process a local project to generate PR."""
    print(f"\nProcessing local project at: {path}")
    
    try:
        # Initialize codebase from local path
        codebase = Codebase.from_local(path)
        
        # Set GitHub token if needed for PR creation
        github_token = get_github_token()
        if hasattr(codebase, "set_github_token"):
            codebase.set_github_token(github_token)
        elif hasattr(codebase, "github_token"):
            codebase.github_token = github_token
        
        # Create the PR agent
        agent = PRCoderAgent(
            codebase=codebase,
            model_provider=params.get("model_provider", "anthropic"),
            model_name=params.get("model_name", "claude-3-7-sonnet-latest"),
        )
        
        # Create branch if specified
        branch_name = params.get("branch_name")
        if branch_name and hasattr(codebase, "checkout"):
            codebase.checkout(branch=branch_name, create_if_missing=True)
            print(f"Switched to branch: {branch_name}")
        
        # Run the agent
        if params.get("use_reflection", True) and hasattr(agent, "run_with_reflection"):
            result = agent.run_with_reflection(requirements)
        else:
            result = agent.generate_pr(
                user_request=requirements,
                branch_name=params.get("branch_name"),
                base_branch=params.get("base_branch")
            )
        
        # Display the result
        print("\nPR Generation Result:")
        print("=" * 80)
        
        if isinstance(result, dict):
            for key, value in result.items():
                if key != "agent_response":
                    print(f"{key}: {value}")
            
            print("\nAgent Response:")
            print("-" * 80)
            if "agent_response" in result:
                print(result["agent_response"])
        else:
            print(result)
        
    except Exception as e:
        print(f"Error processing local project: {e}")
        logger.error(f"Error processing local project: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main function to run the CLI tool."""
    print("\n========================================")
    print("PR Generation CLI Tool")
    print("========================================")
    print("This tool will help you generate a pull request for your project")
    print("using natural language requirements.")
    
    # Get project source and location
    source_type, location = select_project_source()
    
    # Get detailed requirements
    requirements = get_requirements()
    if not requirements.strip():
        print("Error: Requirements cannot be empty.")
        sys.exit(1)
    
    # Get optional parameters
    params = get_optional_parameters()
    
    # Process project according to source type
    if source_type == "github":
        process_github_project(location, requirements, params)
    else:  # local
        process_local_project(location, requirements, params)


def parse_args():
    """Parse command line arguments for non-interactive mode."""
    parser = argparse.ArgumentParser(
        description="Generate code changes and create a pull request based on natural language requirements."
    )
    
    parser.add_argument(
        "--repo", 
        type=str,
        help="Repository string in the format 'owner/repo' (for GitHub projects)"
    )
    
    parser.add_argument(
        "--path", 
        type=str,
        help="Local project path"
    )
    
    parser.add_argument(
        "--request", 
        type=str,
        help="Natural language description of the code changes to implement"
    )
    
    parser.add_argument(
        "--branch", 
        type=str,
        help="Branch name for the changes"
    )
    
    parser.add_argument(
        "--base", 
        type=str,
        help="Base branch name"
    )
    
    parser.add_argument(
        "--model-provider", 
        type=str,
        choices=["anthropic", "openai"],
        default="anthropic",
        help="Model provider to use"
    )
    
    parser.add_argument(
        "--model-name", 
        type=str,
        default="claude-3-7-sonnet-latest",
        help="Model name to use"
    )
    
    parser.add_argument(
        "--no-reflection", 
        action="store_true",
        help="Disable reflection for faster results"
    )
    
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub token (if not provided, will use GITHUB_TOKEN environment variable)"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    # Check if arguments are provided for non-interactive mode
    args = parse_args()
    
    if args.repo or args.path:
        # Non-interactive mode
        if args.request:
            params = {
                "branch_name": args.branch,
                "base_branch": args.base,
                "model_provider": args.model_provider,
                "model_name": args.model_name,
                "use_reflection": not args.no_reflection,
            }
            
            # Set GitHub token from command line or environment
            if args.token:
                os.environ["GITHUB_TOKEN"] = args.token
            
            if args.repo:
                process_github_project(args.repo, args.request, params)
            elif args.path:
                process_local_project(args.path, args.request, params)
        else:
            print("Error: --request argument is required in non-interactive mode.")
            sys.exit(1)
    else:
        # Interactive mode
        try:
            main()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)