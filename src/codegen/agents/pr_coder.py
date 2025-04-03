"""PR Coder Agent for generating code changes and creating pull requests.

This module provides a comprehensive PR Coder Agent that can:
1. Analyze a codebase based on a user request
2. Generate appropriate code changes
3. Create a pull request with the suggested changes
4. Add comments explaining the changes

The agent uses reflection capabilities to improve the quality of generated code
and ensure it matches the user's requirements and project standards.
"""

import os
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from codegen.agents.loggers import ExternalLogger
from codegen.agents.tracer import MessageStreamTracer
from codegen.agents.utils import AgentConfig
from codegen.extensions.langchain.agent import create_codebase_agent
from codegen.extensions.langchain.llm import LLM
from codegen.extensions.langchain.prompts import REASONER_SYSTEM_MESSAGE
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
from codegen.extensions.tools.reflection import perform_reflection, ReflectionObservation
from codegen.extensions.tools.observation import Observation

if TYPE_CHECKING:
    from codegen import Codebase


# Enhanced system prompt for PR code generation
PR_CODER_SYSTEM_PROMPT = """You are an expert software engineer tasked with implementing code changes based on user requests.
Your goal is to analyze the codebase, understand the requirements, and generate high-quality code changes that can be submitted as a pull request.

Follow these steps:
1. Analyze the user's request carefully to understand what changes are needed
2. Search the codebase to find relevant files and understand the existing code structure
3. Plan your changes, considering code organization, maintainability, and project standards
4. Implement the changes with clear, well-documented code
5. Test your changes mentally to ensure they work as expected
6. Prepare a clear PR description explaining what you did and why

Guidelines for high-quality code changes:
- Follow the existing code style and patterns in the project
- Add appropriate comments and documentation
- Consider edge cases and error handling
- Make your changes as focused and minimal as possible while meeting requirements
- Ensure backward compatibility unless explicitly asked to break it

When you're ready to create a PR, use the create_pr tool with a descriptive title and detailed body.
"""


class PRCoderAgent:
    """Agent for generating code changes and creating pull requests based on user requests."""

    codebase: "Codebase"
    agent: CompiledGraph
    langsmith_client: Client
    project_name: str
    thread_id: str | None = None
    run_id: str | None = None
    instance_id: str | None = None
    difficulty: int | None = None
    logger: Optional[ExternalLogger] = None

    def __init__(
        self,
        codebase: "Codebase",
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        tools: Optional[list[BaseTool]] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
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
            thread_id: Optional thread ID for message history
            logger: Optional external logger
            **kwargs: Additional LLM configuration options
        """
        self.codebase = codebase
        
        # Initialize default tools for PR creation
        pr_tools = [
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            RipGrepTool(codebase),
            CreateFileTool(codebase),
            DeleteFileTool(codebase),
            RenameFileTool(codebase),
            RevealSymbolTool(codebase),
            ReplacementEditTool(codebase),
            RelaceEditTool(codebase),
            GlobalReplacementEditTool(codebase),
            SearchFilesByNameTool(codebase),
            GithubCreatePRTool(codebase),
            GithubViewPRTool(codebase),
            GithubCreatePRCommentTool(codebase),
            GithubCreatePRReviewCommentTool(codebase),
        ]
        
        # Add any additional tools
        if tools:
            # Get names of additional tools
            additional_names = {t.name for t in tools}
            # Keep only tools that don't have matching names in additional_tools
            pr_tools = [t for t in pr_tools if t.name not in additional_names]
            pr_tools.extend(tools)
        
        # Create the agent with PR-specific system prompt
        system_message = SystemMessage(PR_CODER_SYSTEM_PROMPT)
        self.agent = create_codebase_agent(
            self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            system_message=system_message,
            memory=memory,
            additional_tools=pr_tools,
            config=agent_config,
            **kwargs,
        )
        
        self.model_name = model_name
        self.langsmith_client = Client()

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
        
        # Extract difficulty value from "difficulty_X" format if present
        difficulty_str = metadata.get("difficulty", "") if metadata else ""
        self.difficulty = int(difficulty_str.split("_")[1]) if difficulty_str and "_" in difficulty_str else None

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

    def run(self, user_request: str, image_urls: Optional[list[str]] = None) -> str:
        """Run the PR Coder agent with a user request and optional images.

        Args:
            user_request: The user's request describing desired code changes
            image_urls: Optional list of base64-encoded image strings

        Returns:
            The agent's response, including PR information if created
        """
        self.config = {
            "configurable": {
                "thread_id": self.thread_id,
                "metadata": {"project": self.project_name},
            },
            "recursion_limit": 100,
        }

        # Prepare content with prompt and images if provided
        content = [{"type": "text", "text": user_request}]
        if image_urls:
            content += [{"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls]

        config = RunnableConfig(
            configurable={"thread_id": self.thread_id}, 
            tags=self.tags, 
            metadata=self.metadata, 
            recursion_limit=200
        )
        
        # Stream the steps to access intermediate nodes
        stream = self.agent.stream(
            {"messages": [HumanMessage(content=content)]}, 
            config=config, 
            stream_mode="values"
        )

        _tracer = MessageStreamTracer(logger=self.logger)

        # Process the stream with the tracer
        traced_stream = _tracer.process_stream(stream)

        # Keep track of run IDs from the stream
        run_ids = []

        for s in traced_stream:
            if len(s["messages"]) == 0 or isinstance(s["messages"][-1], HumanMessage):
                message = HumanMessage(content=content)
            else:
                message = s["messages"][-1]

            if isinstance(message, tuple):
                # print(message)
                pass
            else:
                if isinstance(message, AIMessage) and isinstance(message.content, list) and len(message.content) > 0 and "text" in message.content[0]:
                    AIMessage(message.content[0]["text"]).pretty_print()
                else:
                    message.pretty_print()

                # Try to extract run ID if available in metadata
                if hasattr(message, "additional_kwargs") and "run_id" in message.additional_kwargs:
                    run_ids.append(message.additional_kwargs["run_id"])

        # Get the last message content
        result = s["final_answer"]

        # Try to find run IDs in the LangSmith client's recent runs
        try:
            # Find and print the LangSmith run URL
            find_and_print_langsmith_run_url(self.langsmith_client, self.project_name)
        except Exception as e:
            separator = "=" * 60
            print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
            import traceback
            print(traceback.format_exc())
            print(separator)

        return result

    def run_with_reflection(self, user_request: str, image_urls: Optional[list[str]] = None) -> str:
        """Run the PR Coder agent with reflection for improved results.

        This method enhances the basic run method by adding a reflection step
        that helps the agent improve its code generation by analyzing its own
        understanding and approach.

        Args:
            user_request: The user's request describing desired code changes
            image_urls: Optional list of base64-encoded image strings

        Returns:
            The agent's response, including PR information if created
        """
        # First, analyze the request and codebase to understand what needs to be done
        analysis_prompt = f"""
        I need to implement the following changes to the codebase:
        
        {user_request}
        
        Before I start coding, I need to analyze the codebase to understand its structure and identify which files need to be modified.
        Please help me understand the codebase and plan my approach.
        """
        
        analysis_result = self.run(analysis_prompt, image_urls)
        
        # Perform reflection on the analysis to improve understanding
        reflection = perform_reflection(
            context_summary=f"User request: {user_request}",
            findings_so_far=analysis_result,
            current_challenges="What are the key files that need to be modified? What are potential challenges in implementing these changes?",
            reflection_focus="code implementation strategy",
            codebase=self.codebase
        )
        
        # Use the reflection to guide the implementation
        implementation_prompt = f"""
        I need to implement the following changes to the codebase:
        
        {user_request}
        
        Based on my analysis, here's what I understand about the codebase and what needs to be done:
        
        {analysis_result}
        
        I've reflected on this and have the following insights:
        
        {reflection.render()}
        
        Now, please help me implement these changes and create a pull request with a clear description of what was done.
        """
        
        implementation_result = self.run(implementation_prompt, image_urls)
        
        return implementation_result

    def get_agent_trace_url(self) -> str | None:
        """Get the URL for the most recent agent run in LangSmith.

        Returns:
            The URL for the run in LangSmith if found, None otherwise
        """
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

    def get_tools(self) -> list[BaseTool]:
        """Get the list of tools available to the agent.

        Returns:
            List of BaseTool objects
        """
        return list(self.agent.get_graph().nodes["tools"].data.tools_by_name.values())

    def get_state(self) -> dict:
        """Get the current state of the agent.

        Returns:
            Dictionary containing the agent's state
        """
        return self.agent.get_state(self.config)

    def get_tags_metadata(self) -> tuple[list[str], dict]:
        """Get tags and metadata for the agent.

        Returns:
            Tuple of (tags, metadata)
        """
        tags = [self.model_name]
        metadata = {"project": self.project_name, "model": self.model_name}
        
        # Add run ID and instance ID to the metadata and tags for filtering
        if self.run_id is not None:
            metadata["run_id"] = self.run_id
            tags.append(self.run_id)

        if self.instance_id is not None:
            metadata["instance_id"] = self.instance_id
            tags.append(self.instance_id)

        if self.difficulty is not None:
            metadata["difficulty"] = self.difficulty
            tags.append(f"difficulty_{self.difficulty}")

        return tags, metadata


class PRCoderObservation(Observation):
    """Response from PR code generation."""

    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    pr_title: Optional[str] = None
    files_changed: List[str] = []
    summary: str = ""

    def render_as_string(self, max_tokens: int = 8000) -> str:
        """Render the PR generation result as a string.

        Args:
            max_tokens: Maximum number of tokens to include

        Returns:
            Formatted string representation of the PR result
        """
        if self.status == "error":
            return f"Error: {self.error}"
        
        if self.pr_url:
            result = f"PR created successfully!\n\n"
            result += f"PR #{self.pr_number}: {self.pr_title}\n"
            result += f"URL: {self.pr_url}\n\n"
            
            if self.files_changed:
                result += "Files changed:\n"
                for file in self.files_changed:
                    result += f"- {file}\n"
                result += "\n"
            
            result += f"Summary:\n{self.summary}"
            return result
        else:
            return f"PR creation pending. Summary of planned changes:\n{self.summary}"


def create_pr_agent(
    repo_str: str,
    user_request: str,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-7-sonnet-latest",
    use_reflection: bool = True,
    **kwargs
) -> PRCoderObservation:
    """Create a PR agent and run it with the given user request.

    This is a convenience function that initializes a codebase, creates a PR agent,
    and runs it with the given user request.

    Args:
        repo_str: Repository string in the format "owner/repo"
        user_request: The user's request describing desired code changes
        model_provider: The model provider to use ("anthropic" or "openai")
        model_name: Name of the model to use
        use_reflection: Whether to use reflection for improved results
        **kwargs: Additional parameters to pass to the agent

    Returns:
        PRCoderObservation containing the result of the PR creation
    """
    try:
        # Import here to avoid circular imports
        from codegen import Codebase
        
        # Initialize the codebase
        print(f"Initializing codebase for {repo_str}...")
        codebase = Codebase.from_repo(repo_str)
        
        # Create a unique branch for the changes
        branch_name = f"pr-coder-{uuid.uuid4().hex[:8]}"
        codebase.checkout(branch=branch_name, create_if_missing=True)
        
        # Create the PR agent
        print(f"Creating PR agent with {model_provider}/{model_name}...")
        agent = PRCoderAgent(
            codebase=codebase,
            model_provider=model_provider,
            model_name=model_name,
            **kwargs
        )
        
        # Run the agent with or without reflection
        print(f"Running PR agent with user request: {user_request[:100]}...")
        if use_reflection:
            result = agent.run_with_reflection(user_request)
        else:
            result = agent.run(user_request)
        
        # Parse the result to extract PR information
        pr_url = None
        pr_number = None
        pr_title = None
        files_changed = []
        
        # Try to extract PR information from the result
        import re
        
        # Look for PR URL
        url_match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/\d+', result)
        if url_match:
            pr_url = url_match.group(0)
            # Extract PR number from URL
            pr_number_match = re.search(r'/pull/(\d+)', pr_url)
            if pr_number_match:
                pr_number = int(pr_number_match.group(1))
        
        # Look for PR title
        title_match = re.search(r'PR #\d+: (.+?)[\n\r]', result)
        if title_match:
            pr_title = title_match.group(1)
        elif "Title:" in result:
            title_match = re.search(r'Title: (.+?)[\n\r]', result)
            if title_match:
                pr_title = title_match.group(1)
        
        # Look for files changed
        files_section = re.search(r'Files changed:(.+?)(?:\n\n|\n[A-Z])', result, re.DOTALL)
        if files_section:
            files_text = files_section.group(1)
            files_changed = [f.strip('- \n\r') for f in files_text.split('\n') if f.strip().startswith('-')]
        
        return PRCoderObservation(
            status="success",
            pr_url=pr_url,
            pr_number=pr_number,
            pr_title=pr_title,
            files_changed=files_changed,
            summary=result
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating PR: {e}\n{error_details}")
        
        return PRCoderObservation(
            status="error",
            error=f"Failed to create PR: {str(e)}",
            summary=f"Error details:\n{error_details}"
        )


# Example usage with hardcoded values
if __name__ == "__main__":
    # Hardcoded repository and request for demonstration
    REPO_PATH = "owner/repo"
    USER_REQUEST = """
    Add a new utility function to handle error logging with the following requirements:
    1. Create a new file called error_logger.py in the utils directory
    2. Implement a function that logs errors to both console and file
    3. Add appropriate error levels (INFO, WARNING, ERROR, CRITICAL)
    4. Make sure it's thread-safe
    5. Add documentation and examples
    """
    
    result = create_pr_agent(
        repo_str=REPO_PATH,
        user_request=USER_REQUEST,
        use_reflection=True
    )
    
    print(result.render_as_string())