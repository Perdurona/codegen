"""
Configuration utilities for PR Generation System.

This module provides configuration utilities for the PR Generation System.
"""

import os
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PRGenerationConfig:
    """
    Configuration for PR Generation System.
    
    This class holds configuration settings for the PR Generation System,
    including GitHub tokens, model settings, and default repositories.
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        default_repo: Optional[str] = None,
        default_org: Optional[str] = None,
        default_base_branch: str = "main",
        **kwargs
    ):
        """
        Initialize PR Generation Configuration.
        
        Args:
            github_token: GitHub API token
            model_provider: Model provider (anthropic or openai)
            model_name: Model name to use
            default_repo: Default repository name
            default_org: Default organization name
            default_base_branch: Default base branch for PRs
            **kwargs: Additional configuration parameters
        """
        # Set GitHub token
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            logger.warning("GitHub token not provided and GITHUB_TOKEN environment variable not set")
        
        # Set model settings
        self.model_provider = model_provider
        self.model_name = model_name
        
        # Set repository settings
        self.default_repo = default_repo
        self.default_org = default_org
        self.default_base_branch = default_base_branch
        
        # Set additional parameters
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # Set default full repo if org and repo are specified
        if self.default_org and self.default_repo:
            self.default_full_repo = f"{self.default_org}/{self.default_repo}"
        else:
            self.default_full_repo = None
    
    @classmethod
    def from_env(cls) -> "PRGenerationConfig":
        """
        Create configuration from environment variables.
        
        Environment variables:
            GITHUB_TOKEN: GitHub API token
            MODEL_PROVIDER: Model provider (anthropic or openai)
            MODEL_NAME: Model name
            DEFAULT_REPO: Default repository name
            DEFAULT_ORG: Default organization name
            DEFAULT_BASE_BRANCH: Default base branch
            
        Returns:
            PRGenerationConfig instance
        """
        return cls(
            github_token=os.environ.get("GITHUB_TOKEN"),
            model_provider=os.environ.get("MODEL_PROVIDER", "anthropic"),
            model_name=os.environ.get("MODEL_NAME", "claude-3-7-sonnet-latest"),
            default_repo=os.environ.get("DEFAULT_REPO"),
            default_org=os.environ.get("DEFAULT_ORG"),
            default_base_branch=os.environ.get("DEFAULT_BASE_BRANCH", "main")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary with configuration
        """
        return {
            "github_token": self.github_token,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "default_repo": self.default_repo,
            "default_org": self.default_org,
            "default_base_branch": self.default_base_branch,
            "default_full_repo": self.default_full_repo
        }


# Default configuration
default_config = PRGenerationConfig.from_env()