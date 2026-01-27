"""Agent module for EmpatIA."""

from .empatia_agent import EmpatIAAgent, agent
from .system_prompt import get_system_prompt

__all__ = ["EmpatIAAgent", "agent", "get_system_prompt"]
