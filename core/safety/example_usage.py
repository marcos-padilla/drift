"""
Example usage of safety and approval management features.

This module demonstrates how to use the approval manager to assess
and manage tool call approvals.
"""

import asyncio
import logging
from pathlib import Path

from core.config.loader import load_configuration
from core.safety.approval import ApprovalManager
from core.safety.models import ApprovalContext, ApprovalDecision, ToolConfirmation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_confirmation_callback(confirmation: ToolConfirmation) -> bool:
    """
    Example confirmation callback for user interaction.

    Parameters
    ----------
    confirmation : ToolConfirmation
        Confirmation request.

    Returns
    -------
    bool
        True if user approves, False otherwise.
    """
    print(f"\n⚠️  Approval Request")
    print(f"Tool: {confirmation.tool_name}")
    print(f"Description: {confirmation.description}")
    print(f"Affected paths: {confirmation.context.affected_paths}")
    if confirmation.context.command:
        print(f"Command: {confirmation.context.command}")

    # In a real implementation, this would prompt the user
    # For this example, we'll auto-approve
    response = input("\nApprove? (y/n): ").lower().strip()
    return response == "y"


async def example_approval_workflow() -> None:
    """
    Example of using approval manager in a workflow.

    This example demonstrates:
    - Creating an approval manager
    - Checking approval for different types of actions
    - Handling confirmation requests
    """
    # Load configuration
    config = load_configuration()

    # Create approval manager with confirmation callback
    manager = ApprovalManager(
        config=config,
        confirmation_callback=example_confirmation_callback,
    )

    # Example 1: Safe, non-mutating action (auto-approved)
    safe_context = ApprovalContext(
        tool_name="read_file",
        params={"path": "test.py"},
        is_mutating=False,
        affected_paths=[],
    )
    decision = await manager.check_approval(safe_context)
    print(f"Safe read action: {decision}")
    assert decision == ApprovalDecision.APPROVED

    # Example 2: Mutating action within working directory
    write_context = ApprovalContext(
        tool_name="write_file",
        params={"path": "test.py", "content": "print('hello')"},
        is_mutating=True,
        affected_paths=[Path("test.py")],
    )
    decision = await manager.check_approval(write_context)
    print(f"Write action: {decision}")

    # Example 3: Dangerous command
    dangerous_context = ApprovalContext(
        tool_name="shell",
        params={"command": "rm -rf /"},
        is_mutating=True,
        affected_paths=[],
        command="rm -rf /",
        is_dangerous=True,
    )
    decision = await manager.check_approval(dangerous_context)
    print(f"Dangerous command: {decision}")
    assert decision in {
        ApprovalDecision.REJECTED,
        ApprovalDecision.NEEDS_CONFIRMATION,
    }

    # Example 4: Action requiring confirmation
    if decision == ApprovalDecision.NEEDS_CONFIRMATION:
        confirmation = ToolConfirmation(
            tool_name=dangerous_context.tool_name,
            description="Execute potentially dangerous command",
            context=dangerous_context,
        )
        approved = await manager.request_confirmation(confirmation)
        print(f"User approved: {approved}")


if __name__ == "__main__":
    asyncio.run(example_approval_workflow())
