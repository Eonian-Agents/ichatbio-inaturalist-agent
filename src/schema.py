"""
This module provides pydantic schema used to craft and validate iNaturalist API queries.
"""
from datetime import date
from math import isclose
from typing import Optional, List, Union, Literal

from pydantic import Field, BaseModel, ValidationInfo, field_validator, model_validator

from request_constraints import (
    BOUNDING_BOX_FIELDS, explicit_search_constraints, requires_bounding_box,
)

class ObservationsQueryParams(BaseModel):
    """
    This schema models request parameters to the iNaturalist observations API at https://www.inaturalist.org/observations.json
    """
    q: Optional[str] = Field(None, description="Search query string. Best used alone for free-text searching.")
    page: Optional[int] = Field(None, ge=1, description="Page number (1-based)")
    per_page: Optional[int] = Field(default=200, ge=1, le=200, description="Number of results per page (1-200)")
    limit: Optional[int] = Field(None, ge=1, description="Total number of results to fetch across all pages. Defaults to 200, but can be set higher (up to 10,000).")
    
    
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

    @model_validator(mode="before")
    @classmethod
    def apply_explicit_request_constraints(cls, values, info: ValidationInfo):
        # The user's labelled numbers are authoritative. Apply them before the
        # field/range validators so missing or incorrect model values can be repaired.
        if isinstance(values, dict):
            request = (info.context or {}).get("user_request", "")
            return {**values, **explicit_search_constraints(request)}
        return values

    @field_validator("d1", "d2", "updated_since", mode="before")
    @classmethod
    def parse_iso_dates(cls, value):
        # Instructor validates Python dictionaries in strict mode. JSON date
        # strings need conversion before strict Pydantic date validation.
        return date.fromisoformat(value) if isinstance(value, str) else value

    @field_validator("extra", "has", "iconic_taxa")
    @classmethod
    def remove_duplicate_options(cls, values):
        return list(dict.fromkeys(values)) if values is not None else None

    @model_validator(mode="after")
    def validate_ranges(self):
        provided = [field for field in BOUNDING_BOX_FIELDS if getattr(self, field) is not None]
        if provided and len(provided) != len(BOUNDING_BOX_FIELDS):
            raise ValueError(
                "A bounding box requires all four coordinates: swlat, swlng, nelat, nelng. "
                f"Missing: {', '.join(field for field in BOUNDING_BOX_FIELDS if field not in provided)}"
            )
        if self.swlat is not None and self.swlat > self.nelat:
            raise ValueError("Bounding box swlat must be less than or equal to nelat.")
        if self.d1 is not None and self.d2 is not None and self.d1 > self.d2:
            raise ValueError("Date range d1 must be less than or equal to d2.")
        return self

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

    @model_validator(mode="after")
    def preserve_request_constraints(self, info: ValidationInfo):
        request = (info.context or {}).get("user_request", "")
        params = self.search_parameters.model_dump(mode="json")
        if requires_bounding_box(request) and any(
            params[field] is None for field in BOUNDING_BOX_FIELDS
        ):
            raise ValueError(
                "The request specifies a bounding box. Include swlat, swlng, nelat, and nelng; "
                "do not replace the requested area with an unbounded query."
            )
        errors = []
        for field, expected in explicit_search_constraints(request).items():
            actual = params[field]
            matches = (
                actual is not None and isclose(actual, expected, rel_tol=0, abs_tol=1e-9)
                if isinstance(expected, float) else actual == expected
            )
            if not matches:
                errors.append(f"{field} must be {expected!r}, received {actual!r}")
        if errors:
            raise ValueError("Preserve the request's explicit search constraints: " + "; ".join(errors))
        return self


class INaturalistEntrypointParams(BaseModel):
    query_start: Optional[str] = Field(None, description="ISO-8601 wall-clock time (UTC) when the user query started")
