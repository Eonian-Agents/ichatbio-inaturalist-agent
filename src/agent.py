from typing import override, Optional

import dotenv
from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext
from ichatbio.server import build_agent_app
from ichatbio.types import AgentCard
from pydantic import BaseModel
from starlette.applications import Starlette

from entrypoints import search_inaturalist_observations


class INaturalistAgent(IChatBioAgent):
    @override
    def get_agent_card(self) -> AgentCard:
        return AgentCard(
            name="iNaturalist Observation Search",
            description="Searches for observations in iNaturalist (https://inaturalist.org).",
            documentation_url="https://github.com/acislab/ichatbio-inaturalist-agent",
            icon='https://static.inaturalist.org/wiki_page_attachments/3154-medium.png',
            entrypoints=[
                search_inaturalist_observations.entrypoint
            ]
        )

    @override
    async def run(self, context: ResponseContext, request: str, entrypoint: str, params: Optional[BaseModel]):
        match entrypoint:
            case search_inaturalist_observations.entrypoint.id:
                await search_inaturalist_observations.run(context, request, params)
            case _:
                raise ValueError()


def create_app() -> Starlette:
    dotenv.load_dotenv()
    agent = INaturalistAgent()
    app = build_agent_app(agent)
    return app
