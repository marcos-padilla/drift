"""
Session persistence for saving and loading agent sessions.

This module provides functionality to save and load agent session state
for resuming conversations and creating checkpoints.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config.loader import get_data_dir
from core.llm.models import TokenUsage

logger = logging.getLogger(__name__)


class SessionSnapshot:
    """
    Snapshot of agent session state.

    Parameters
    ----------
    session_id : str
        Unique session identifier.
    created_at : datetime
        Session creation timestamp.
    updated_at : datetime
        Last update timestamp.
    turn_count : int
        Number of conversation turns.
    messages : list[dict[str, Any]]
        Conversation messages.
    total_usage : TokenUsage
        Cumulative token usage.

    Examples
    --------
    >>> snapshot = SessionSnapshot(
    ...     session_id="123",
    ...     created_at=datetime.now(),
    ...     updated_at=datetime.now(),
    ...     turn_count=5,
    ...     messages=[],
    ...     total_usage=TokenUsage()
    ... )
    """

    def __init__(
        self,
        session_id: str,
        created_at: datetime,
        updated_at: datetime,
        turn_count: int,
        messages: list[dict[str, Any]],
        total_usage: TokenUsage,
    ) -> None:
        self.session_id: str = session_id
        self.created_at: datetime = created_at
        self.updated_at: datetime = updated_at
        self.turn_count: int = turn_count
        self.messages: list[dict[str, Any]] = messages
        self.total_usage: TokenUsage = total_usage

    def to_dict(self) -> dict[str, Any]:
        """
        Convert snapshot to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the snapshot.
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "messages": self.messages,
            "total_usage": self.total_usage.model_dump(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionSnapshot":
        """
        Create snapshot from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary representation.

        Returns
        -------
        SessionSnapshot
            Snapshot instance.
        """
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            turn_count=data["turn_count"],
            messages=data["messages"],
            total_usage=TokenUsage(**data["total_usage"]),
        )


class PersistenceManager:
    """
    Manages session persistence and checkpoints.

    This class provides functionality to save and load agent sessions
    and create checkpoints for recovery.

    Examples
    --------
    >>> manager = PersistenceManager()
    >>> manager.save_session(snapshot)
    >>> snapshot = manager.load_session("session_id")
    """

    def __init__(self) -> None:
        self.data_dir: Path = get_data_dir()
        self.sessions_dir: Path = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir: Path = self.data_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.sessions_dir, 0o700)
        os.chmod(self.checkpoints_dir, 0o700)

    def save_session(self, snapshot: SessionSnapshot) -> None:
        """
        Save a session snapshot.

        Parameters
        ----------
        snapshot : SessionSnapshot
            Session snapshot to save.

        Examples
        --------
        >>> manager.save_session(snapshot)
        """
        file_path: Path = self.sessions_dir / f"{snapshot.session_id}.json"

        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(snapshot.to_dict(), fp, indent=2)

        os.chmod(file_path, 0o600)
        logger.debug(f"Saved session: {snapshot.session_id}")

    def load_session(self, session_id: str) -> SessionSnapshot | None:
        """
        Load a session snapshot.

        Parameters
        ----------
        session_id : str
            Session ID to load.

        Returns
        -------
        SessionSnapshot | None
            Session snapshot if found, None otherwise.

        Examples
        --------
        >>> snapshot = manager.load_session("session_id")
        """
        file_path: Path = self.sessions_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                data: dict[str, Any] = json.load(fp)

            return SessionSnapshot.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(self) -> list[dict[str, Any]]:
        """
        List all saved sessions.

        Returns
        -------
        list[dict[str, Any]]
            List of session metadata dictionaries.

        Examples
        --------
        >>> sessions = manager.list_sessions()
        >>> for session in sessions:
        ...     print(f"{session['session_id']}: {session['turn_count']} turns")
        """
        sessions: list[dict[str, Any]] = []
        for file_path in self.sessions_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as fp:
                    data: dict[str, Any] = json.load(fp)
                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "turn_count": data["turn_count"],
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to load session from {file_path}: {e}")

        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    def save_checkpoint(self, snapshot: SessionSnapshot) -> str:
        """
        Save a checkpoint of a session.

        Parameters
        ----------
        snapshot : SessionSnapshot
            Session snapshot to checkpoint.

        Returns
        -------
        str
            Checkpoint ID.

        Examples
        --------
        >>> checkpoint_id = manager.save_checkpoint(snapshot)
        """
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id: str = f"{snapshot.session_id}_{timestamp}"
        file_path: Path = self.checkpoints_dir / f"{checkpoint_id}.json"

        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(snapshot.to_dict(), fp, indent=2)
        os.chmod(file_path, 0o600)
        logger.debug(f"Saved checkpoint: {checkpoint_id}")
        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> SessionSnapshot | None:
        """
        Load a checkpoint.

        Parameters
        ----------
        checkpoint_id : str
            Checkpoint ID to load.

        Returns
        -------
        SessionSnapshot | None
            Session snapshot if found, None otherwise.

        Examples
        --------
        >>> snapshot = manager.load_checkpoint("checkpoint_id")
        """
        file_path: Path = self.checkpoints_dir / f"{checkpoint_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                data: dict[str, Any] = json.load(fp)

            return SessionSnapshot.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None
