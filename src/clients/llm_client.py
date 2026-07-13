# src/clients/llm_client.py

import logging
import os

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM client with Groq primary + Ollama fallback."""

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
        self.fallback_enabled = os.getenv("GROQ_FALLBACK", "ollama") == "ollama"

        self._groq = None
        self._ollama = None

    def _get_groq(self):
        if self._groq is None and self.groq_api_key:
            self._groq = ChatGroq(
                api_key=self.groq_api_key,
                model=self.model,
                temperature=0.1,
            )
        return self._groq

    def _get_ollama(self):
        if self._ollama is None and self.fallback_enabled:
            model = os.getenv("OLLAMA_MODEL_QUALITY", "llama3.1:8b")
            self._ollama = ChatOllama(model=model, temperature=0.1)
        return self._ollama

    def generate(self, prompt: str) -> str:
        """Generate response from LLM with fallback."""
        # Try Groq first
        groq = self._get_groq()
        if groq:
            try:
                response = groq.invoke([HumanMessage(content=prompt)])
                return response.content
            except Exception as e:
                logger.warning(f"Groq failed: {e}")
                logger.error(f"Groq failed with error: {e}")  # ← Add this line
                logger.error(f"Groq error type: {type(e)}")  # ← Add this line

        # Fallback to Ollama
        ollama = self._get_ollama()
        if ollama:
            try:
                logger.info("Falling back to Ollama")
                response = ollama.invoke([HumanMessage(content=prompt)])
                return response.content
            except Exception as e:
                logger.error(f"Ollama also failed: {e}")

        raise RuntimeError("No LLM available (Groq and Ollama both failed)")
