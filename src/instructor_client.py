from llm_config import MODEL, create_instructor_client


def get_model_name() -> str:
    return MODEL


async def get_client():
    return create_instructor_client()
