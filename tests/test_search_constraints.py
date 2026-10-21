import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from openai import AsyncOpenAI
from pydantic import ValidationError

import llm_config
from entrypoints import search_inaturalist_observations as search
from schema import LLMGeneration, ObservationsQueryParams
from request_constraints import explicit_search_constraints


REQUEST = (
    "[ORCHESTRATED] Search iNaturalist for ALL Fungi observations (complete fetch, no sampling) "
    "within the bounding box decimalLatitude 44.144 to 44.280 and decimalLongitude "
    "-122.297 to -122.147 for the year 2022 (dates 2022-01-01 to 2022-12-31). "
    "This bounding box represents a 2000m radius around the CENMET station at HJ Andrews "
    "Forest (44.212°N, 122.222°W) with a 0.05° buffer. Include geographic coordinates "
    "(latitude, longitude) and observation dates for each record. Use taxon_name=Fungi."
)
BOUNDS = {"swlat": 44.144, "swlng": -122.297, "nelat": 44.280, "nelng": -122.147}
EXPECTED = {**BOUNDS, "d1": "2022-01-01", "d2": "2022-12-31", "taxon_name": "Fungi"}
BROKEN = {"per_page": 200, "taxon_name": "Fungi", "nelat": 44.28, "nelng": -122.147,
          "extra": ["observation_photos", "observation_photos"]}


@pytest.mark.parametrize("params", [BROKEN, {"swlat": 0}, {"swlng": -122.297, "nelng": -122.147}])
def test_incomplete_bounding_box_is_rejected(params):
    with pytest.raises(ValidationError, match="all four coordinates"):
        ObservationsQueryParams.model_validate(params)


@pytest.mark.parametrize("params", [
    {"taxon_name": "Fungi"},
    BOUNDS,
    BROKEN,
    {**EXPECTED, "swlat": 44.212},
    {**EXPECTED, "d2": "2023-12-31"},
    {**EXPECTED, "swlat": "not a coordinate", "d1": "not a date"},
])
def test_explicit_request_constraints_repair_missing_or_incorrect_model_values(params):
    original = params.copy()
    result = LLMGeneration.model_validate(
        {"artifact_description": "Fungi observations", "search_parameters": params},
        context={"user_request": REQUEST},
    )
    actual = result.search_parameters.model_dump(mode="json")
    for field in (*BOUNDS, "d1", "d2"):
        assert actual[field] == EXPECTED[field]
    assert params == original


def test_explicit_api_coordinates_and_dates_are_preserved():
    request = (
        "Fungi within swlat=44.144, swlng=-122.297, nelat=44.280, nelng=-122.147 "
        "with d1=2022-01-01 and d2=2022-12-31"
    )
    result = LLMGeneration.model_validate(
        {"artifact_description": "Fungi", "search_parameters": {**EXPECTED, "swlng": -122.2}},
        context={"user_request": request},
    )
    assert result.search_parameters.swlng == -122.297


def test_latest_reported_request_repairs_model_output_without_another_model_call():
    user_request = (
        "[ORCHESTRATED] Search iNaturalist for ALL Fungi observations (complete fetch, "
        "paginate through all results) within the bounding box decimalLatitude 44.174 "
        "to 44.250 and decimalLongitude -122.267 to -122.177 (2000m radius around CENMET "
        "station at HJ Andrews, 44.212N 122.222W, with 0.02 degree buffer) for the full "
        "year 2022 (2022-01-01 to 2022-12-31). Request geographic coordinates (latitude, "
        "longitude), observation dates, taxon information (scientific name, taxon ID), "
        "and observation IDs. This is a complete fetch - retrieve all matching records, "
        "not just a sample."
    )
    result = LLMGeneration.model_validate(
        {"artifact_description": "Fungi", "search_parameters": BROKEN},
        context={"user_request": user_request},
    )
    actual = result.search_parameters.model_dump(mode="json")
    for field, expected in {
        "swlat": 44.174, "nelat": 44.250, "swlng": -122.267, "nelng": -122.177,
        "d1": "2022-01-01", "d2": "2022-12-31",
    }.items():
        assert actual[field] == expected


def test_box_without_explicit_numbers_still_rejects_an_unbounded_query():
    with pytest.raises(ValidationError, match="bounding box"):
        LLMGeneration.model_validate(
            {"artifact_description": "Fungi", "search_parameters": {"taxon_name": "Fungi"}},
            context={"user_request": "Fungi in the bounding box from our previous conversation"},
        )


def test_unbounded_search_remains_valid_and_options_are_deduplicated():
    result = LLMGeneration.model_validate(
        {"artifact_description": "Fungi", "search_parameters": {
            "taxon_name": "Fungi", "extra": ["observation_photos", "observation_photos"],
        }},
        context={"user_request": "Find Fungi observations with photos"},
    )
    assert result.search_parameters.extra == ["observation_photos"]


@pytest.mark.parametrize("user_request", [
    "Fungi for the full year 2022",
    "Fungi for the year 2022",
    "Fungi in 2022",
])
def test_year_only_requests_keep_the_date_filter(user_request):
    assert explicit_search_constraints(user_request) == {"d1": "2022-01-01", "d2": "2022-12-31"}


def test_explicit_date_interval_takes_precedence_over_year_description():
    assert explicit_search_constraints(
        "Fungi in 2022, specifically 2022-06-01 to 2022-08-31",
    ) == {"d1": "2022-06-01", "d2": "2022-08-31"}


def test_center_point_is_not_mistaken_for_bounds():
    assert explicit_search_constraints(
        "Fungi around a station at latitude 44.212 and longitude -122.222 with a 0.05° buffer",
    ) == {}


def test_iso_dates_are_accepted_under_instructor_strict_validation():
    params = ObservationsQueryParams.model_validate(
        {"d1": "2022-01-01", "d2": "2022-12-31", "updated_since": "2023-01-01"},
        strict=True,
    )
    assert params.model_dump(mode="json")["d1"] == "2022-01-01"


def test_invalid_date_is_not_silently_accepted():
    with pytest.raises(ValidationError):
        ObservationsQueryParams.model_validate({"d1": "2022-02-30"}, strict=True)


@pytest.mark.parametrize("params", [
    {**BOUNDS, "swlat": 45},
    {"d1": "2023-01-01", "d2": "2022-01-01"},
])
def test_reversed_ranges_are_rejected(params):
    with pytest.raises(ValidationError):
        ObservationsQueryParams.model_validate(params)


def model_response(params):
    return httpx.Response(200, json={
        "id": "local-test", "object": "chat.completion", "created": 0,
        "model": "local-test",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant", "content": json.dumps({
                "artifact_description": "Fungi observations in the requested area during 2022",
                "search_parameters": params,
            }),
        }}],
    })


@pytest.mark.asyncio
async def test_instructor_repairs_dropped_constraints_on_first_response(monkeypatch):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return model_response(BROKEN)

    async with AsyncOpenAI(
        api_key="local-test", base_url="http://model.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ) as raw_client:
        monkeypatch.setattr(llm_config, "create_openai_client", lambda: raw_client)
        params, _ = await search._generate_observations_params(REQUEST)

    assert len(requests) == 1
    assert all(body["reasoning_effort"] == "low" for body in requests)
    url_params = parse_qs(urlparse(search.build_query_url(
        "https://api.inaturalist.org/v1/observations", params,
    )).query)
    for key, expected in EXPECTED.items():
        assert url_params[key] == [str(expected)]


@pytest.mark.asyncio
async def test_repeated_invalid_generation_never_reaches_observation_api(monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return model_response({**BROKEN, "per_page": 201})

    logs = []
    process = SimpleNamespace(log=AsyncMock(side_effect=lambda message, **_: logs.append(message)))

    @asynccontextmanager
    async def begin_process(_):
        yield process

    api = AsyncMock()
    monkeypatch.setattr(search, "query_inaturalist_observations", api)
    async with AsyncOpenAI(
        api_key="local-test", base_url="http://model.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ) as raw_client:
        monkeypatch.setattr(llm_config, "create_openai_client", lambda: raw_client)
        await search.run(SimpleNamespace(begin_process=begin_process), REQUEST)

    assert len(calls) == 3
    api.assert_not_awaited()
    assert logs[-1] == "Error: AI failed to generate valid output after 3 attempts."
