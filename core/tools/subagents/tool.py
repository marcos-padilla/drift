"""
Subagent tool for spawning specialized sub-agents.

This module provides a tool that spawns sub-agents with specific goals
and limited tool access for specialized tasks.
"""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from core.agent.agent import Agent
from core.agent.events import AgentEventType
from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.tools.subagents.models import SubagentDefinition

logger = logging.getLogger(__name__)


class SubagentParams(BaseModel):
    """
    Parameters for the subagent tool.

    Parameters
    ----------
    goal : str
        The specific task or goal for the subagent to accomplish.

    Examples
    --------
    >>> params = SubagentParams(goal="Find all functions that use async/await")
    """

    goal: str = Field(
        ...,
        description="The specific task or goal for the subagent to accomplish",
    )


class SubagentTool(Tool):
    """
    Tool for spawning specialized sub-agents.

    This tool creates a sub-agent with a specific goal and limited tool
    access to accomplish specialized tasks like codebase investigation
    or code review.

    Parameters
    ----------
    config : Configuration
        Configuration object.
    definition : SubagentDefinition
        Subagent definition with goal and constraints.

    Attributes
    ----------
    definition : SubagentDefinition
        Subagent definition.
    name : str
        Tool name (derived from definition).
    description : str
        Tool description (derived from definition).
    kind : ToolKind
        Tool kind: MEMORY (considered mutating as it uses agent resources).
    schema : type[SubagentParams]
        Parameter schema.
    """

    def __init__(self, config, definition: SubagentDefinition) -> None:
        super().__init__(config)
        self.definition: SubagentDefinition = definition

    @property
    def name(self) -> str:
        """
        Get the tool name.

        Returns
        -------
        str
            Tool name in format "subagent_{definition_name}".
        """
        return f"subagent_{self.definition.name}"

    @property
    def description(self) -> str:
        """
        Get the tool description.

        Returns
        -------
        str
            Tool description from definition.
        """
        return self.definition.description

    schema: type[SubagentParams] = SubagentParams
    kind: ToolKind = ToolKind.MEMORY

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """
        Check if the tool operation is mutating.

        Subagents are considered mutating as they consume resources
        and may perform actions.

        Parameters
        ----------
        params : dict[str, Any]
            Tool parameters (not used).

        Returns
        -------
        bool
            Always True for subagents.
        """
        return True

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the subagent tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters.

        Returns
        -------
        ToolResult
            Result containing subagent execution summary.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = SubagentParams(**invocation.params)
        if not params.goal:
            return ToolResult.error_result("No goal specified for sub-agent")

        # Create subagent configuration
        config_dict = self.config.to_dict()
        config_dict["max_turns"] = self.definition.max_turns
        if self.definition.allowed_tools:
            config_dict["allowed_tools"] = self.definition.allowed_tools

        from core.config.schema import Configuration

        subagent_config = Configuration(**config_dict)

        prompt: str = f"""You are a specialized sub-agent with a specific task to complete.

{self.definition.goal_prompt}

YOUR TASK:
{params.goal}

IMPORTANT:
- Focus only on completing the specified task
- Do not engage in unrelated actions
- Once you have completed the task or have the answer, provide your final response
- Be concise and direct in your output
"""

        tool_calls: list[str] = []
        final_response: str | None = None
        error: str | None = None
        terminate_response: str = "goal"

        try:
            async with Agent(subagent_config) as agent:
                deadline: float = (
                    asyncio.get_event_loop().time()
                    + self.definition.timeout_seconds
                )

                async for event in agent.run(prompt):
                    if asyncio.get_event_loop().time() > deadline:
                        terminate_response = "timeout"
                        final_response = "Sub-agent timed out"
                        break

                    if event.type == AgentEventType.TOOL_CALL_START:
                        tool_calls.append(event.data.get("name", "unknown"))
                    elif event.type == AgentEventType.TEXT_COMPLETE:
                        final_response = event.data.get("content")
                    elif event.type == AgentEventType.AGENT_END:
                        if final_response is None:
                            final_response = event.data.get("response")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        terminate_response = "error"
                        error = event.data.get("error", "Unknown")
                        final_response = f"Sub-agent error: {error}"
                        break
        except Exception as e:
            logger.exception(f"Subagent '{self.definition.name}' failed: {e}")
            terminate_response = "error"
            error = str(e)
            final_response = f"Sub-agent failed: {e}"

        result: str = f"""Sub-agent '{self.definition.name}' completed. 
Termination: {terminate_response}
Tools called: {', '.join(tool_calls) if tool_calls else 'None'}

Result:
{final_response or 'No response'}
"""

        if error:
            return ToolResult.error_result(result)

        return ToolResult.success_result(result)
