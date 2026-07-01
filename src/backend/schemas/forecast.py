from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class ForecastOut(BaseModel):
    park:         str
    date:         date
    fire_prob:    float
    drought_prob: float
    veg_prob:     float
    computed_at:  datetime

    model_config = {"from_attributes": True}


class ParkOverview(BaseModel):
    park:         str
    latest_date:  date                    # data date the forecast is anchored to
    fire_prob:    float
    drought_prob: float
    veg_prob:     float
    computed_at:  Optional[datetime] = None   # when the daily job last refreshed it


class Driver(BaseModel):
    label:  str
    value:  str
    impact: str   # "raises" | "lowers"


class DriversResponse(BaseModel):
    park:    str
    date:    str
    probs:   dict                 # {fire, drought, vegetation}
    drivers: dict                 # {threat: [Driver, ...]}