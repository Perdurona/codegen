"""PR Coder Agent for generating code changes and creating pull requests.

This module provides a comprehensive PR agent that can:
1. Analyze a codebase based on a user request
2. Generate appropriate code changes
3. Create a pull request with the suggested changes
"""

import os
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig

from codegen.agents.loggers import ExternalLogger
from codegen.agents.tracer import MessageStreamTracer
from codegen.extensions.langchain.agent import create_codebase_agent
from codegen.extensions.langchain.tools import (
    CreateFileTool,
    DeleteFileTool,
    GithubCreatePRTool,
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
    GlobalReplacementEditTool,
    ListDirectoryTool,
    RelaceEditTool,
    RenameFileTool,
    ReplacementEditTool,
    RevealSymbolTool,
    RipGrepTool,
    SearchFilesByNameTool,
    ViewFileTool,
)
from codegen.extensions.langchain.utils.get_langsmith_url import (
    find_and_print_langsmith_run_url,
)
from codegen.agents.utils import AgentConfig

# Import for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from codegen import Codebase
    from langsmith import Client


class PRCoderAgent:
    """Agent for generating code changes and creating pull requests based on user requests."""

    codebase: "Codebase"
    agent: Any  # CompiledGraph
    langsmith_client: Optional["Client"] = None
    project_name: str
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    instance_id: Optional[str] = None
    logger: Optional[ExternalLogger] = None
    
    def __init__(
        self,
        codebase: "Codebase",
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        tools: Optional[List[BaseTool]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_config: Optional[AgentConfig] = None,
        thread_id: Optional[str] = None,
        logger: Optional[ExternalLogger] = None,
        **kwargs,
    ):
        """Initialize a PRCoderAgent.

        Args:
            codebase: The codebase to operate on
            model_provider: The model provider to use ("anthropic" or "openai")
            model_name: Name of the model to use
            memory: Whether to let LLM keep track of the conversation history
            tools: Additional tools to use
            tags: Tags to add to the agent trace
            metadata: Metadata to use for the agent
            agent_config: Configuration for the agent
            thread_id: Thread ID for message history
            logger: External logger for agent actions
            **kwargs: Additional LLM configuration options
        """
        self.codebase = codebase
        
        # Set up PR-specific tools
        pr_tools = [
            # Code analysis tools
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            RipGrepTool(codebase),
            SearchFilesByNameTool(codebase),
            RevealSymbolTool(codebase),
            
            # Code modification tools
            CreateFileTool(codebase),
            DeleteFileTool(codebase),
            RenameFileTool(codebase),
            ReplacementEditTool(codebase),
            RelaceEditTool(codebase),
            GlobalReplacementEditTool(codebase),
            
            # GitHub PR tools
            GithubCreatePRTool(codebase),
            GithubViewPRTool(codebase),
            GithubCreatePRCommentTool(codebase),
            GithubCreatePRReviewCommentTool(codebase),
        ]
        
        # Add any additional tools provided
        if tools:
            additional_names = {t.name for t in tools}
            pr_tools = [t for t in pr_tools if t.name not in additional_names]
            pr_tools.extend(tools)
        
        # Create the agent
        self.agent = create_codebase_agent(
            self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            additional_tools=pr_tools,
            config=agent_config,
            **kwargs,
        )
        
        self.model_name = model_name
        
        # Set up LangSmith for tracing
        try:
            from langsmith import Client
            self.langsmith_client = Client()
        except (ImportError, Exception):
            self.langsmith_client = None
        
        # Set thread ID
        if thread_id is None:
            self.thread_id = str(uuid.uuid4())
        else:
            self.thread_id = thread_id
        
        # Get project name from environment variable or use a default
        self.project_name = os.environ.get("LANGCHAIN_PROJECT", "CODEGEN_PR")
        print(f"Using LangSmith project: {self.project_name}")
        
        # Store metadata if provided
        self.run_id = metadata.get("run_id") if metadata else None
        self.instance_id = metadata.get("instance_id") if metadata else None
        
        # Initialize tags for agent trace
        self.tags = [*(tags or []), self.model_name]
        
        # Set logger if provided
        self.logger = logger
        
        # Initialize metadata for agent trace
        self.metadata = {
            "project": self.project_name,
            "model": self.model_name,
            **(metadata or {}),
        }

    def generate_pr(self, user_request: str, branch_name: Optional[str] = None, base_branch: Optional[str] = None) -> Dict[str, Any]:
        """Generate code changes and create a PR based on a user request.
        
        Args:
            user_request: The user's request describing the desired code changes
            branch_name: Optional name for the branch to create (if None, will generate one)
            base_branch: Optional name for the base branch (if None, will use repo default)
            
        Returns:
            Dictionary with PR information including URL, title, and branch
        """
        # Generate a unique branch name if not provided
        if not branch_name:
            short_request = user_request.split()[0:3]
            short_request = "-".join(short_request).lower()
            short_request = "".join(c if c.isalnum() or c == "-" else "-" for c in short_request)
            branch_name = f"codegen-{short_request}-{str(uuid.uuid4())[:8]}"
        
        # Create a prompt that instructs the agent to analyze the codebase and make changes
        prompt = f"""
You are an expert software engineer tasked with implementing code changes based on a user request.

USER REQUEST: {user_request}

Follow these steps:
1. Analyze the codebase to understand its structure and the relevant components
2. Identify the files that need to be modified or created
3. Make the necessary code changes to implement the request
4. Create a pull request with a descriptive title and detailed description

When creating the PR:
- Use the branch name: {branch_name}
- If a base branch is specified, use: {base_branch or 'the repository default branch'}
- Include a clear title that summarizes the changes
- Write a detailed description explaining what you did and why
- Reference any relevant files or components

Make sure your changes are well-tested and follow the existing code style and patterns.
"""
        
        # Run the agent with the prompt
        result = self.run(prompt)
        
        # Extract PR information from the result
        # This is a simplified approach - in a real implementation, we would parse the agent's response
        # to extract the PR URL, title, and other details
        pr_info = {
            "branch_name": branch_name,
            "base_branch": base_branch,
            "user_request": user_request,
            "agent_response": result,
            # Additional fields would be populated based on the actual PR creation
        }
        
        return pr_info

    def run(self, prompt: str, image_urls: Optional[List[str]] = None) -> str:
        """Run the agent with a prompt and optional images.

        Args:
            prompt: The prompt to run
            image_urls: Optional list of image URLs

        Returns:
            The agent's response
        """
        self.config = {
            "configurable": {
                "thread_id": self.thread_id,
                "metadata": {"project": self.project_name},
            },
            "recursion_limit": 100,
        }

        # Prepare content with prompt and images if provided
        content = [{"type": "text", "text": prompt}]
        if image_urls:
            content += [{"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls]

        config = RunnableConfig(
            configurable={"thread_id": self.thread_id}, 
            tags=self.tags, 
            metadata=self.metadata, 
            recursion_limit=200
        )
        
        # Stream the agent's execution
        stream = self.agent.stream(
            {"messages": [HumanMessage(content=content)]}, 
            config=config, 
            stream_mode="values"
        )

        _tracer = MessageStreamTracer(logger=self.logger)
        traced_stream = _tracer.process_stream(stream)

        # Process the stream
        run_ids = []
        for s in traced_stream:
            if len(s["messages"]) == 0 or isinstance(s["messages"][-1], HumanMessage):
                message = HumanMessage(content=content)
            else:
                message = s["messages"][-1]

            if isinstance(message, tuple):
                pass
            else:
                if isinstance(message, AIMessage) and isinstance(message.content, list) and len(message.content) > 0 and "text" in message.content[0]:
                    AIMessage(message.content[0]["text"]).pretty_print()
                else:
                    message.pretty_print()

                # Try to extract run ID if available in metadata
                if hasattr(message, "additional_kwargs") and "run_id" in message.additional_kwargs:
                    run_ids.append(message.additional_kwargs["run_id"])

        # Get the final answer
        result = s["final_answer"]

        # Try to find and print the LangSmith run URL
        if self.langsmith_client:
            try:
                find_and_print_langsmith_run_url(self.langsmith_client, self.project_name)
            except Exception as e:
                separator = "=" * 60
                print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
                import traceback
                print(traceback.format_exc())
                print(separator)

        return result

    def get_agent_trace_url(self) -> Optional[str]:
        """Get the URL for the most recent agent run in LangSmith.

        Returns:
            The URL for the run in LangSmith if found, None otherwise
        """
        if not self.langsmith_client:
            return None
            
        try:
            return find_and_print_langsmith_run_url(
                client=self.langsmith_client, 
                project_name=self.project_name
            )
        except Exception as e:
            separator = "=" * 60
            print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
            import traceback
            print(traceback.format_exc())
            print(separator)
            return None


def create_pr_agent(
    repo_str: str,
    user_request: str,
    branch_name: Optional[str] = None,
    base_branch: Optional[str] = None,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-7-sonnet-latest",
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a PR agent and generate a PR based on a user request.
    
    Args:
        repo_str: Repository string in the format "owner/repo"
        user_request: The user's request describing the desired code changes
        branch_name: Optional name for the branch to create
        base_branch: Optional name for the base branch
        model_provider: The model provider to use
        model_name: Name of the model to use
        github_token: Optional GitHub token (if not provided, will use environment variable)
        
    Returns:
        Dictionary with PR information
    """
    from codegen import Codebase
    from codegen.secrets import SecretsConfig
    
    # Set up GitHub token
    if github_token is None:
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GitHub token not provided and GITHUB_TOKEN environment variable not set")
    
    # Initialize codebase
    codebase = Codebase.from_repo(
        repo_str,
        secrets=SecretsConfig(github_token=github_token)
    )
    
    # Create PR agent
    agent = PRCoderAgent(
        codebase=codebase,
        model_provider=model_provider,
        model_name=model_name,
    )
    
    # Generate PR
    pr_info = agent.generate_pr(
        user_request=user_request,
        branch_name=branch_name,
        base_branch=base_branch,
    )
    
    return pr_info


# Example usage with hardcoded inputs
if __name__ == "__main__":
    # Hardcoded repository and request
    REPO = "owner/repo"
    REQUEST = "Add a new utility function to handle error logging"
    
    # Create PR agent and generate PR
    pr_info = create_pr_agent(
        repo_str=REPO,
        user_request=REQUEST,
    )
    
    print(f"PR created with branch: {pr_info.get('branch_name')}")
    print(f"Agent response: {pr_info.get('agent_response')}")