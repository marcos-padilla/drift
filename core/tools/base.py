"""
Base tool class and abstract interface.

This module provides the abstract base class for all tools in the system,
with parameter validation, schema generation, and safety checking.
"""

import abc
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic.json_schema import model_json_schema

from core.config.schema import Configuration
from core.tools.interfaces import ToolProtocol
from core.tools.models import (
    ToolConfirmation,
    ToolInvocation,
    ToolKind,
    ToolResult,
)

# Re-export for convenience
__all__ = ["Tool", "ToolKind"]


class Tool(abc.ABC):
    """
    Abstract base class for all tools.

    All tools must inherit from this class and implement the required
    methods. Tools can define their parameters using Pydantic models
    or dictionaries.

    Parameters
    ----------
    config : Configuration
        Configuration object with settings and context.

    Attributes
    ----------
    name : str
        Unique name of the tool (must be set by subclasses).
    description : str
        Human-readable description (must be set by subclasses).
    kind : ToolKind
        Category of tool operation (must be set by subclasses).
    config : Configuration
        Configuration object.

    Examples
    --------
    >>> class MyTool(Tool):
    ...     name = "my_tool"
    ...     description = "Does something useful"
    ...     kind = ToolKind.READ
    ...     schema = MyParams
    ...
    ...     async def execute(self, invocation: ToolInvocation) -> ToolResult:
    ...         return ToolResult.success_result("Done")
    """

    name: str = "base_tool"
    description: str = "Base tool"
    kind: ToolKind = ToolKind.READ

    def __init__(self, config: Configuration) -> None:
        self.config: Configuration = config

    @property
    def schema(self) -> dict[str, Any] | type[BaseModel]:
        """
        Get the parameter schema for this tool.

        Returns
        -------
        dict[str, Any] | type[BaseModel]
            Either a Pydantic model class or a dictionary schema.

        Raises
        ------
        NotImplementedError
            If not implemented by subclass.
        """
        raise NotImplementedError(
            "Tool must define schema property or class attribute",
        )

    @abc.abstractmethod
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the tool with the given invocation.

        Parameters
        ----------
        invocation : ToolInvocation
            Invocation context with parameters and working directory.

        Returns
        -------
        ToolResult
            Result of the tool execution.

        Raises
        ------
        Exception
            Various exceptions may be raised depending on the tool.
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Validate tool parameters against the schema.

        Parameters
        ----------
        params : dict[str, Any]
            Parameters to validate.

        Returns
        -------
        list[str]
            List of validation error messages. Empty list if valid.

        Examples
        --------
        >>> errors = tool.validate_params({"path": "test.py"})
        >>> if errors:
        ...     print("Validation failed:", errors)
        """
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                schema(**params)
            except ValidationError as e:
                errors: list[str] = []
                for error in e.errors():
                    field = ".".join(str(x) for x in error.get("loc", []))
                    msg = error.get("msg", "Validation error")
                    errors.append(f"Parameter '{field}': {msg}")

                return errors
            except Exception as e:
                return [str(e)]

        return []

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """
        Check if the tool operation modifies system state.

        Parameters
        ----------
        params : dict[str, Any]
            Tool parameters (not used in base implementation).

        Returns
        -------
        bool
            True if the tool kind indicates a mutating operation.

        Examples
        --------
        >>> if tool.is_mutating(params):
        ...     # Requires approval
        """
        return self.kind in {
            ToolKind.WRITE,
            ToolKind.SHELL,
            ToolKind.NETWORK,
            ToolKind.MEMORY,
        }

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for mutating operations.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request if operation is mutating, None otherwise.

        Examples
        --------
        >>> confirmation = await tool.get_confirmation(invocation)
        >>> if confirmation:
        ...     # Request user approval
        """
        if not self.is_mutating(invocation.params):
            return None

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Execute {self.name}",
        )

    def to_openai_schema(self) -> dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema format.

        Returns
        -------
        dict[str, Any]
            OpenAI-compatible function schema.

        Raises
        ------
        ValueError
            If schema type is invalid.

        Examples
        --------
        >>> schema = tool.to_openai_schema()
        >>> # Returns: {"name": "tool_name", "description": "...", "parameters": {...}}
        """
        schema = self.schema

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schema = model_json_schema(schema, mode="serialization")

            return {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": json_schema.get("properties", {}),
                    "required": json_schema.get("required", []),
                },
            }

        if isinstance(schema, dict):
            result: dict[str, Any] = {
                "name": self.name,
                "description": self.description,
            }

            if "parameters" in schema:
                result["parameters"] = schema["parameters"]
            else:
                result["parameters"] = schema

            return result

        raise ValueError(
            f"Invalid schema type for tool {self.name}: {type(schema)}",
        )
