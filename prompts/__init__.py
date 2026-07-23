"""
Prompts module for the Autonomous Research Scientist.
"""

from prompts.teacher_prompts import (
    get_teacher_prompt,
    build_prompt_context,
    BEGINNER_PROMPT,
    INTERMEDIATE_PROMPT,
    EXPERT_PROMPT,
)

__all__ = [
    "get_teacher_prompt",
    "build_prompt_context",
    "BEGINNER_PROMPT",
    "INTERMEDIATE_PROMPT",
    "EXPERT_PROMPT",
]