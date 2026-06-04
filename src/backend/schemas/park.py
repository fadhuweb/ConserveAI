from typing import Optional
from pydantic import BaseModel


class ParkMeta(BaseModel):
    id:           str
    display_name: str
    state:        str
    ecosystem:    str
    area_km2:     int
    lat:          float
    lon:          float


class CatalogItem(BaseModel):
    id:                    str
    name:                  str
    type:                  str
    cost_usd:              float
    max_units:             int
    effectiveness_fire:    float
    effectiveness_drought: float
    effectiveness_veg:     float
    citation:              Optional[str]

    model_config = {"from_attributes": True}


class ZoneOut(BaseModel):
    id:      int
    park_id: str
    name:    str
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    model_config = {"from_attributes": True}