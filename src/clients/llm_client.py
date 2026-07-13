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
        self.groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
        self.model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.fallback_enabled = os.getenv("GROQ_FALLBACK", "ollama") == "ollama"

        self._groq = None
        self._ollama = None

    def _get_groq(self):
        if not self.groq_api_key:
            return None
        if self._groq is None:
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
        groq = self._get_groq()
        if groq:
            try:
                response = groq.invoke([HumanMessage(content=prompt)])
                return response.content
            except Exception as e:
                logger.warning(f"Groq failed ({type(e).__name__}): {e}")
        else:
            logger.warning(
                "GROQ_API_KEY is missing or empty — skipping Groq "
                "(set it in .env, then restart Streamlit)"
            )

        ollama = self._get_ollama()
        if ollama:
            try:
                logger.info("Trying Ollama fallback")
                response = ollama.invoke([HumanMessage(content=prompt)])
                return response.content
            except Exception as e:
                logger.error(f"Ollama failed ({type(e).__name__}): {e}")
        elif self.fallback_enabled:
            logger.warning("Ollama fallback enabled but client could not be created")

        raise RuntimeError(
            "No LLM available. Set GROQ_API_KEY in .env, or start Ollama "
            f"({os.getenv('OLLAMA_MODEL_QUALITY', 'llama3.1:8b')}) with GROQ_FALLBACK=ollama."
        )
