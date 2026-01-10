"""
Approval management for tool calls and command execution.

This module provides functionality to assess safety and manage approvals
for tool calls based on configuration policies and command patterns.
"""

import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from core.config.schema import ApprovalPolicy, Configuration
from core.safety.models import ApprovalContext, ApprovalDecision, ToolConfirmation
from core.safety.patterns import is_dangerous_command, is_safe_command

logger = logging.getLogger(__name__)

# Type alias for confirmation callback
ConfirmationCallback = Callable[[ToolConfirmation], bool | Awaitable[bool]]


class ApprovalManager:
    """
    Manages approval decisions for tool calls and commands.

    This class evaluates tool calls and commands against safety patterns
    and approval policies to determine if they should be approved,
    rejected, or require user confirmation.

    Parameters
    ----------
    config : Configuration
        Configuration object containing approval policy and working directory.
    confirmation_callback : ConfirmationCallback | None, optional
        Callback function to request user confirmation. If None, defaults
        to auto-approving when confirmation is needed.

    Attributes
    ----------
    approval_policy : ApprovalPolicy
        The approval policy to use for decisions.
    cwd : Path
        Current working directory for path validation.
    confirmation_callback : ConfirmationCallback | None
        Callback for requesting user confirmation.

    Examples
    --------
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> manager = ApprovalManager(config)
    >>> context = ApprovalContext(
    ...     tool_name="write_file",
    ...     params={"path": "test.py"},
    ...     is_mutating=True,
    ...     affected_paths=[Path("test.py")]
    ... )
    >>> decision = await manager.check_approval(context)
    """

    def __init__(
        self,
        config: Configuration,
        confirmation_callback: ConfirmationCallback | None = None,
    ) -> None:
        self.approval_policy: ApprovalPolicy = config.approval
        self.cwd: Path = config.cwd
        self.confirmation_callback: ConfirmationCallback | None = confirmation_callback

    def _assess_command_safety(self, command: str) -> ApprovalDecision:
        """
        Assess the safety of a shell command.

        Parameters
        ----------
        command : str
            The shell command to assess.

        Returns
        -------
        ApprovalDecision
            Decision based on command safety and approval policy.

        Examples
        --------
        >>> decision = manager._assess_command_safety("rm -rf /")
        >>> # Returns ApprovalDecision.REJECTED
        """
        if self.approval_policy == ApprovalPolicy.YOLO:
            logger.debug(f"YOLO policy: auto-approving command: {command[:50]}")
            return ApprovalDecision.APPROVED

        if is_dangerous_command(command):
            logger.warning(f"Dangerous command detected: {command[:50]}")
            return ApprovalDecision.REJECTED

        if self.approval_policy == ApprovalPolicy.NEVER:
            if is_safe_command(command):
                logger.debug(f"Safe command auto-approved: {command[:50]}")
                return ApprovalDecision.APPROVED
            logger.info(f"Command requires approval (NEVER policy): {command[:50]}")
            return ApprovalDecision.REJECTED

        if self.approval_policy in {ApprovalPolicy.AUTO, ApprovalPolicy.ON_FAILURE}:
            logger.debug(f"Auto policy: approving command: {command[:50]}")
            return ApprovalDecision.APPROVED

        if self.approval_policy == ApprovalPolicy.AUTO_EDIT:
            if is_safe_command(command):
                logger.debug(f"Safe command auto-approved (AUTO_EDIT): {command[:50]}")
                return ApprovalDecision.APPROVED
            logger.info(f"Command needs confirmation (AUTO_EDIT): {command[:50]}")
            return ApprovalDecision.NEEDS_CONFIRMATION

        # Default: ON_REQUEST policy
        if is_safe_command(command):
            logger.debug(f"Safe command auto-approved: {command[:50]}")
            return ApprovalDecision.APPROVED

        logger.info(f"Command needs confirmation: {command[:50]}")
        return ApprovalDecision.NEEDS_CONFIRMATION

    async def check_approval(self, context: ApprovalContext) -> ApprovalDecision:
        """
        Check if an action should be approved based on context.

        Parameters
        ----------
        context : ApprovalContext
            Context information about the action to approve.

        Returns
        -------
        ApprovalDecision
            Decision on whether to approve, reject, or request confirmation.

        Examples
        --------
        >>> context = ApprovalContext(
        ...     tool_name="write_file",
        ...     params={"path": "test.py"},
        ...     is_mutating=True,
        ...     affected_paths=[Path("test.py")]
        ... )
        >>> decision = await manager.check_approval(context)
        >>> if decision == ApprovalDecision.NEEDS_CONFIRMATION:
        ...     # Request user confirmation
        """
        # Non-mutating actions are always approved
        if not context.is_mutating:
            logger.debug(f"Non-mutating action approved: {context.tool_name}")
            return ApprovalDecision.APPROVED

        # Assess command safety if command is provided
        if context.command:
            decision: ApprovalDecision = self._assess_command_safety(context.command)
            if decision != ApprovalDecision.NEEDS_CONFIRMATION:
                return decision

        # Check if all affected paths are within the working directory
        for path in context.affected_paths:
            try:
                if path.is_relative_to(self.cwd):
                    continue
                else:
                    logger.warning(
                        f"Path outside working directory: {path} "
                        f"(cwd: {self.cwd})",
                    )
                    return ApprovalDecision.NEEDS_CONFIRMATION
            except ValueError:
                # Path is not relative (e.g., absolute path on different drive)
                logger.warning(
                    f"Path cannot be relative to cwd: {path} " f"(cwd: {self.cwd})",
                )
                return ApprovalDecision.NEEDS_CONFIRMATION

        # Check if action is flagged as dangerous
        if context.is_dangerous:
            if self.approval_policy == ApprovalPolicy.YOLO:
                logger.warning(
                    f"YOLO policy: approving dangerous action: {context.tool_name}",
                )
                return ApprovalDecision.APPROVED
            logger.warning(
                f"Dangerous action requires confirmation: {context.tool_name}",
            )
            return ApprovalDecision.NEEDS_CONFIRMATION

        logger.debug(f"Action approved: {context.tool_name}")
        return ApprovalDecision.APPROVED

    async def request_confirmation(
        self,
        confirmation: ToolConfirmation,
    ) -> bool:
        """
        Request user confirmation for a tool call.

        Parameters
        ----------
        confirmation : ToolConfirmation
            Confirmation request with tool details.

        Returns
        -------
        bool
            True if confirmed, False if rejected.

        Examples
        --------
        >>> confirmation = ToolConfirmation(
        ...     tool_name="write_file",
        ...     description="Write file test.py",
        ...     context=approval_context
        ... )
        >>> approved = await manager.request_confirmation(confirmation)
        """
        if self.confirmation_callback:
            result = self.confirmation_callback(confirmation)
            # Handle both sync and async callbacks
            if isinstance(result, Awaitable):
                return await result
            return result

        # Default: auto-approve if no callback provided
        logger.warning(
            f"No confirmation callback provided, auto-approving: "
            f"{confirmation.tool_name}",
        )
        return True
