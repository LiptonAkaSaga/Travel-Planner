"""LLM service — supports OpenAI-compatible and Google Gemini providers."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import config


class LLMService:
    """Wrapper around LLM APIs via LangChain.

    Supports two providers:
    - openai: OpenAI-compatible API (mimo, etc.)
    - google: Google Gemini API
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "",
        api_key: str = "",
    ) -> None:
        """Initialize LLM service.

        Args:
            provider: 'openai' or 'google'.
            model: Model name override. If empty, uses config default.
            api_key: API key override. If empty, uses config default.
        """
        self._provider = provider

        if provider == "google":
            self._init_google(model, api_key)
        else:
            self._init_openai(model, api_key)

    def _init_openai(self, model: str = "", api_key: str = "") -> None:
        """Initialize OpenAI-compatible client."""
        key = api_key or config.OPENAI_API_KEY
        if not key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")

        kwargs: dict = {
            "model": model or config.OPENAI_MODEL,
            "openai_api_key": key,
            "temperature": 0.7,
        }
        if config.OPENAI_BASE_URL:
            kwargs["openai_api_base"] = config.OPENAI_BASE_URL

        self._llm = ChatOpenAI(**kwargs)

    def _init_google(self, model: str = "", api_key: str = "") -> None:
        """Initialize Google Gemini client."""
        key = api_key or config.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY is required for Google provider")

        from langchain_google_genai import ChatGoogleGenerativeAI

        self._llm = ChatGoogleGenerativeAI(
            model=model or config.GEMINI_MODEL,
            google_api_key=key,
            temperature=0.7,
        )

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
