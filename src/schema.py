"""
This module provides pydantic schema used to craft and validate iNaturalist API queries.
"""
from datetime import date
from typing import Optional, List, Union, Literal

from pydantic import Field, BaseModel, EmailStr, field_validator
from pydantic_core import PydanticCustomError

class ObservationsQueryParams(BaseModel):
    """
    This schema models request parameters to the iNaturalist observations API at https://www.inaturalist.org/observations.json
    """
    q: Optional[str] = Field(None, description="Search query string. Best used alone for free-text searching.")
    page: Optional[int] = Field(None, ge=1, description="Page number (1-based)")
    per_page: Optional[int] = Field(default=200, ge=1, le=200, description="Number of results per page (1-200)")
    
    order_by: Optional[Literal["observed_on", "date_observed", "date_added", "created_at"]] = Field(
        None, description="Field to sort by"
    )
    order: Optional[Literal["asc", "desc"]] = Field(
        None, description="Sort order: ascending or descending"
    )
    
    license: Optional[Literal[
        "none", "any", "CC-BY", "CC-BY-NC", "CC-BY-SA", "CC-BY-ND", 
        "CC-BY-NC-SA", "CC-BY-NC-ND"
    ]] = Field(None, description="Filter by license applied to the observation")
    
    photo_license: Optional[Literal[
        "none", "any", "CC-BY", "CC-BY-NC", "CC-BY-SA", "CC-BY-ND", 
        "CC-BY-NC-SA", "CC-BY-NC-ND"
    ]] = Field(None, description="Filter by license applied to associated photos")

    taxon_id: Optional[Union[int, str]] = Field(None, description="iNat taxon ID. Can be a comma-separated list. Includes descendant taxa.")
    taxon_name: Optional[str] = Field(None, description="iNat taxon name. Includes descendant taxa. May match multiple taxa.")
    
    iconic_taxa: Optional[List[Literal[
        "Plantae", "Animalia", "Mollusca", "Reptilia", "Aves", "Amphibia", 
        "Actinopterygii", "Mammalia", "Insecta", "Arachnida", "Fungi", 
        "Protozoa", "Chromista", "unknown"
    ]]] = Field(None, description="Filter by one or more iconic taxa")

    has: Optional[List[Literal["photos", "geo"]]] = Field(
        None, description="Boolean selectors. E.g., 'photos' for observations with photos, 'geo' for georeferenced observations."
    )

    quality_grade: Optional[Literal["casual", "research"]] = Field(
        None, description="Filter by observation quality grade"
    )
    out_of_range: Optional[bool] = Field(
        None, description="Whether observation is considered out of range for the taxon by iNat"
    )

    on: Optional[str] = Field(
        None, description="Filter by date string (yyyy-mm-dd, yyyy-mm, or yyyy)"
    )
    year: Optional[Union[int, str]] = Field(None, description="Filter by year (e.g., 2022 or '2018,2025')")
    month: Optional[Union[int, str]] = Field(None, description="Filter by month (1–12) or comma-separated list")
    day: Optional[Union[int, str]] = Field(None, description="Filter by day of the month (1–31) or comma-separated list")

    d1: Optional[date] = Field(None, description="Start of date range (yyyy-mm-dd)")
    d2: Optional[date] = Field(None, description="End of date range (yyyy-mm-dd)")
    m1: Optional[int] = Field(None, ge=1, le=12, description="Start of month range (1–12)")
    m2: Optional[int] = Field(None, ge=1, le=12, description="End of month range (1–12)")
    h1: Optional[int] = Field(None, ge=0, le=23, description="Start of hour range (0–23)")
    h2: Optional[int] = Field(None, ge=0, le=23, description="End of hour range (0–23)")

    swlat: Optional[float] = Field(None, ge=-90, le=90, description="Southwest latitude of bounding box (-90 to 90)")
    swlng: Optional[float] = Field(None, ge=-180, le=180, description="Southwest longitude of bounding box (-180 to 180)")
    nelat: Optional[float] = Field(None, ge=-90, le=90, description="Northeast latitude of bounding box (-90 to 90)")
    nelng: Optional[float] = Field(None, ge=-180, le=180, description="Northeast longitude of bounding box (-180 to 180)")

    list_id: Optional[int] = Field(None, description="iNat list ID. Limits results to taxa on specified list (max 2000 taxa)")
    updated_since: Optional[date] = Field(None, description="Filter by observations updated since a given ISO8601 datetime")

    extra: Optional[List[Literal["fields", "identifications", "projects", "observation_photos"]]] = Field(
        None, description="Request additional information such as observation fields, project memberships, etc."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "taxon_id": 42048,
                "iconic_taxa": ["Mammalia"],
                "has": ["photos", "geo"],
                "quality_grade": "research",
                "page": 1,
                "per_page": 50
            }
        }


class LLMGeneration(BaseModel):
    artifact_description: str = Field(
        description="A concise characterization of the observation data to be retrieved",
        examples=["Rattus Rattus observations in iNaturalist",
                  "Galax Urceolata iNaturalist observations since 2015"])
    search_parameters: ObservationsQueryParams = Field()


class INaturalistEntrypointParams(BaseModel):
    query_start: Optional[str] = Field(None, description="ISO-8601 wall-clock time (UTC) when the user query started")
