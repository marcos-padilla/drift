"""
Default subagent definitions.

This module provides pre-configured subagent definitions for common
use cases like codebase investigation and code review.
"""

from core.tools.subagents.models import SubagentDefinition

CODEBASE_INVESTIGATOR = SubagentDefinition(
    name="codebase_investigator",
    description=(
        "Investigates the codebase to answer questions about code structure, "
        "patterns, and implementations"
    ),
    goal_prompt="""You are a codebase investigation specialist.
Your job is to explore and understand code to answer questions.
Use read_file, grep, glob, and list_dir to investigate.
Do NOT modify any files.""",
    allowed_tools=["read_file", "grep", "glob", "list_dir"],
)

CODE_REVIEWER = SubagentDefinition(
    name="code_reviewer",
    description=(
        "Reviews code changes and provides feedback on quality, bugs, "
        "and improvements"
    ),
    goal_prompt="""You are a code review specialist.
Your job is to review code and provide constructive feedback.
Look for bugs, code smells, security issues, and improvement opportunities.
Use read_file, list_dir and grep to examine the code.
Do NOT modify any files.""",
    allowed_tools=["read_file", "grep", "list_dir"],
    max_turns=10,
    timeout_seconds=300.0,
)


def get_default_subagent_definitions() -> list[SubagentDefinition]:
    """
    Get all default subagent definitions.

    Returns
    -------
    list[SubagentDefinition]
        List of default subagent definitions.

    Examples
    --------
    >>> definitions = get_default_subagent_definitions()
    >>> for defn in definitions:
    ...     print(f"{defn.name}: {defn.description}")
    """
    return [
        CODEBASE_INVESTIGATOR,
        CODE_REVIEWER,
    ]
