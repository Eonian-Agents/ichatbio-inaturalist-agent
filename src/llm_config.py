"""Shared model connection settings for this agent service."""
import os

import instructor
from openai import AsyncOpenAI, DefaultAsyncHttpxClient

MODEL = os.getenv("AGENT_LLM_MODEL", "qwen-3.8-27b")


def create_openai_client() -> AsyncOpenAI:
    options = {
        "base_url": os.getenv("AGENT_LLM_BASE_URL", "https://llm.jetstream-cloud.org/qwen-3.8-27b/v1/"),
        "api_key": os.getenv("AGENT_LLM_API_KEY", "unused"),
        "timeout": 240,
        "max_retries": 2,
    }
    if proxy := os.getenv("AGENT_LLM_PROXY"):
        options["http_client"] = DefaultAsyncHttpxClient(proxy=proxy)
    return AsyncOpenAI(**options)


def create_instructor_client():
    return instructor.from_openai(
        create_openai_client(), model=MODEL, mode=instructor.Mode.JSON_SCHEMA,
    )
