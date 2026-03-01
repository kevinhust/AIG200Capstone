import logging
import os
import requests
from typing import Any, Dict, List, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all agents in the swarm.
    
    Each agent has a specific role and system prompt that defines its specialty.
    All agents share common execution logic but differ in their prompts and tools.
    
    Supports multiple LLM backends:
    - Google Gemini (default)
    - OpenAI-compatible APIs (xAI Grok, DeepSeek, etc.)
    """
    
    def __init__(
        self, 
        role: str, 
        system_prompt: str, 
        use_openai_api: bool = True,
        api_config: Optional[Dict[str, str]] = None
    ):
        """
        Initialize a base agent.
        
        Args:
            role: The agent's role identifier (e.g., "coder", "reviewer").
            system_prompt: The system prompt defining the agent's behavior.
            use_openai_api: If True, use OpenAI-compatible API (xAI/DeepSeek).
                           If False, use Google Gemini.
            api_config: Optional dict with 'base_url', 'api_key', 'model' to override defaults.
        """
        self.role = role
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict[str, str]] = []
        self.use_openai_api = use_openai_api
        self.api_config = api_config or {}
        
        # Initialize client based on mode
        running_under_pytest = "PYTEST_CURRENT_TEST" in os.environ
        if running_under_pytest:
            self.client = None  # Will use dummy response in execute()
        elif not use_openai_api:
            # Initialize Gemini client
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            except Exception as e:
                print(f"⚠️ {role} agent: genai client not initialized: {e}")
                self.client = None
        else:
            # OpenAI-compatible mode - no client needed, uses requests
            self.client = None
    
    def _call_openai_api(self, prompt: str) -> str:
        """
        Call OpenAI-compatible API (xAI Grok, DeepSeek, etc.).
        
        Args:
            prompt: The full prompt to send.
            
        Returns:
            The model's response text.
        """
        # Prefer specific config, fall back to global settings
        base_url = self.api_config.get('base_url') or getattr(settings, 'OPENAI_BASE_URL', '').rstrip("/")
        api_key = self.api_config.get('api_key') or getattr(settings, 'OPENAI_API_KEY', '')
        model = self.api_config.get('model') or getattr(settings, 'OPENAI_MODEL', 'grok-2-latest')
        
        if not base_url:
            return f"[{self.role}] Error: API Base URL not configured"
        
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096  # Increased for GLM/Grok
        }

        # Add specific parameters for reasoning models if needed
        if "reasoning" in model.lower():
            # Some providers might need specific flags, usually standard chat completions work
            pass
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content if content else str(data)
        except requests.RequestException as e:
            return f"[{self.role}] Error calling API ({model}): {e}"
    
    def _call_gemini_api(self, prompt: str) -> str:
        """
        Call Google Gemini API.
        
        Args:
            prompt: The full prompt to send.
            
        Returns:
            The model's response text.
        """
        if not self.client:
            return f"[{self.role}] Error: Gemini client not initialized"
        
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt
            )
            return getattr(response, "text", str(response)).strip()
        except Exception as e:
            logger.error(f"[{self.role}] Error executing task: {str(e)}\n(Quota might be exhausted)")
            return f"[{self.role}] Error executing task: {str(e)}\n(Quota might be exhausted)"
    
    def execute(self, task: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Execute a task with optional context from other agents.
        """
        if "PYTEST_CURRENT_TEST" in os.environ:
            return f"[{self.role}] Task completed"

        prompt_parts = [f"Task: {task}"]
        if context:
            context_str = "\n\nContext from other agents:\n"
            for msg in context:
                context_str += f"[{msg.get('from', 'unknown')}]: {msg.get('content', '')}\n"
            prompt_parts.append(context_str)
        
        full_prompt = "".join(prompt_parts)
        
        if self.use_openai_api:
            result = self._call_openai_api(full_prompt)
        else:
            result = self._call_gemini_api(self.system_prompt + "\n\n" + full_prompt)
        
        self.conversation_history.append({"role": "user", "content": task})
        self.conversation_history.append({"role": "assistant", "content": result})
        
        return result
    async def _call_openai_api_async(self, prompt: str) -> str:
        """Asynchronous call to OpenAI-compatible API."""
        import aiohttp
        base_url = self.api_config.get('base_url') or getattr(settings, 'OPENAI_BASE_URL', '').rstrip("/")
        api_key = self.api_config.get('api_key') or getattr(settings, 'OPENAI_API_KEY', '')
        model = self.api_config.get('model') or getattr(settings, 'OPENAI_MODEL', 'grok-2-latest')
        
        if not base_url:
            return f"[{self.role}] Error: API Base URL not configured"
        
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=120) as response:
                    response.raise_for_status()
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content if content else str(data)
        except Exception as e:
            return f"[{self.role}] Error calling API ({model}): {e}"

    async def _call_gemini_api_async(self, prompt: str) -> str:
        """Asynchronous call to Google Gemini API."""
        if not self.client:
            return f"[{self.role}] Error: Gemini client not initialized"
        
        try:
            import asyncio
            # Wrap synchronous generate_content in a thread to keep it async-friendly
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt
            )
            return getattr(response, "text", str(response)).strip()
        except Exception as e:
            return f"[{self.role}] Error executing task: {str(e)}"

    async def execute_async(self, task: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        """Asynchronously execute a task."""
        if "PYTEST_CURRENT_TEST" in os.environ:
            return f"[{self.role}] Task completed"
        
        prompt_parts = [f"Task: {task}"]
        if context:
            context_str = "\n\nContext from other agents:\n"
            for msg in context:
                context_str += f"[{msg.get('from', 'unknown')}]: {msg.get('content', '')}\n"
            prompt_parts.append(context_str)
        
        full_prompt = "".join(prompt_parts)
        
        if self.use_openai_api:
            result = await self._call_openai_api_async(full_prompt)
        else:
            result = await self._call_gemini_api_async(self.system_prompt + "\n\n" + full_prompt)
        
        self.conversation_history.append({"role": "user", "content": task})
        self.conversation_history.append({"role": "assistant", "content": result})
        
        return result
    
    def reset_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
