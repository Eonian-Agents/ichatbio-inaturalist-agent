import os

import instructor
from openai import AsyncOpenAI


def get_model_name() -> str:
    return (os.getenv("INATURALIST_MODEL") or os.getenv("AGENTS_LLM") or "gpt-5.1-mini").strip()


async def get_client():
    api_key = os.getenv("INATURALIST_API_KEY") or os.getenv("OPENAI_API_KEY")
    return instructor.from_openai(AsyncOpenAI(api_key=api_key), model=get_model_name())

