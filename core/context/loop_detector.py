"""
Loop detection for identifying repetitive patterns in agent behavior.

This module provides functionality to detect when an agent is stuck in
repetitive loops, which can help prevent infinite loops and improve
conversation quality.
"""

import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


class LoopDetector:
    """
    Detects repetitive patterns and loops in agent actions.

    This class tracks action history and identifies when the same actions
    are being repeated, which may indicate the agent is stuck.

    Parameters
    ----------
    max_exact_repeats : int, default=3
        Maximum number of exact action repeats before flagging.
    max_cycle_length : int, default=3
        Maximum cycle length to detect.

    Attributes
    ----------
    max_exact_repeats : int
        Maximum exact repeats threshold.
    max_cycle_length : int
        Maximum cycle length to detect.
    _history : deque[str]
        History of action signatures.

    Examples
    --------
    >>> detector = LoopDetector()
    >>> detector.record_action("tool_call", tool_name="search", args={"query": "test"})
    >>> loop_description = detector.check_for_loop()
    >>> if loop_description:
    ...     print(f"Loop detected: {loop_description}")
    """

    def __init__(
        self,
        max_exact_repeats: int = 3,
        max_cycle_length: int = 3,
    ) -> None:
        self.max_exact_repeats: int = max_exact_repeats
        self.max_cycle_length: int = max_cycle_length
        self._history: deque[str] = deque(maxlen=20)

    def record_action(self, action_type: str, **details: Any) -> None:
        """
        Record an action for loop detection.

        Parameters
        ----------
        action_type : str
            Type of action (e.g., "tool_call", "response").
        **details : Any
            Additional details about the action.

        Examples
        --------
        >>> detector.record_action(
        ...     "tool_call",
        ...     tool_name="read_file",
        ...     args={"path": "main.py"}
        ... )
        """
        output: list[str] = [action_type]

        if action_type == "tool_call":
            output.append(details.get("tool_name", ""))
            args = details.get("args", {})

            if isinstance(args, dict):
                for k in sorted(args.keys()):
                    output.append(f"{k}={str(args[k])}")
        elif action_type == "response":
            output.append(details.get("text", ""))

        signature: str = "|".join(output)
        self._history.append(signature)
        logger.debug(f"Recorded action: {signature}")

    def check_for_loop(self) -> str | None:
        """
        Check if a loop pattern is detected in the action history.

        Returns
        -------
        str | None
            Description of the detected loop if found, None otherwise.

        Examples
        --------
        >>> loop_description = detector.check_for_loop()
        >>> if loop_description:
        ...     print(f"Warning: {loop_description}")
        """
        if len(self._history) < 2:
            return None

        # Check for exact repeats
        if len(self._history) >= self.max_exact_repeats:
            recent: list[str] = list(self._history)[-self.max_exact_repeats :]
            if len(set(recent)) == 1:
                return (
                    f"Same action repeated {self.max_exact_repeats} times: {recent[0]}"
                )

        # Check for cycles
        if len(self._history) >= self.max_cycle_length * 2:
            history: list[str] = list(self._history)

            for cycle_len in range(
                2,
                min(self.max_cycle_length + 1, len(history) // 2 + 1),
            ):
                recent = history[-cycle_len * 2 :]
                if recent[:cycle_len] == recent[cycle_len:]:
                    return f"Detected repeating cycle of length {cycle_len}"

        return None

    def clear(self) -> None:
        """
        Clear the action history.

        Examples
        --------
        >>> detector.clear()
        """
        self._history.clear()
        logger.debug("Loop detector history cleared")
