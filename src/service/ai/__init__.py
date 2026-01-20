"""
AI Analysis Service Module.

Provides AI-powered market analysis using multiple providers:
- OpenAI (ChatGPT)
- Ollama (local LLM)

Features:
- Daily market summaries
- Weekly analysis reports
- Trading opportunity analysis
- Risk assessment
"""

from service.ai.analyzer import MarketAnalyzer
from service.ai.providers import AIService, OllamaProvider, OpenAIProvider

__all__ = [
    "AIService",
    "OpenAIProvider",
    "OllamaProvider",
    "MarketAnalyzer",
]
