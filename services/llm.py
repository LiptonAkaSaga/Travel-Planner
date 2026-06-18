"""LLM service using OpenAI API via LangChain."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import config


class LLMService:
    """Wrapper around OpenAI API via LangChain."""

    def __init__(self, api_key: str = "") -> None:
        key = api_key or config.OPENAI_API_KEY
        if not key:
            raise ValueError("OPENAI_API_KEY is required")

        kwargs: dict = {
            "model": config.OPENAI_MODEL,
            "openai_api_key": key,
            "temperature": 0.7,
        }
        if config.OPENAI_BASE_URL:
            kwargs["openai_api_base"] = config.OPENAI_BASE_URL

        self._llm = ChatOpenAI(**kwargs)

    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a chat request to the LLM.

        Args:
            system_prompt: System instructions for the model.
            user_message: User's message.

        Returns:
            Model's response as a string.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = self._llm.invoke(messages)
        return response.content

    def chat_with_structured_output(self, system_prompt: str, user_message: str, schema: type) -> dict:
        """Send a chat request expecting structured JSON output.

        Args:
            system_prompt: System instructions.
            user_message: User's message.
            schema: Pydantic model for structured output.

        Returns:
            Parsed response as a dictionary.
        """
        structured_llm = self._llm.with_structured_output(schema)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = structured_llm.invoke(messages)
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response
