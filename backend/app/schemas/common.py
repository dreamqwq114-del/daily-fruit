from decimal import Decimal
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
)


def _decimal_as_number(value: Decimal) -> float:
    return float(value)


DecimalAsNumber = PlainSerializer(
    _decimal_as_number,
    return_type=float,
    when_used="json",
)

PositiveId = Annotated[int, Field(gt=0)]
Month = Annotated[int, Field(ge=1, le=12)]
RefreshNumber = Annotated[int, Field(ge=0)]
NormalizedScore = Annotated[
    Decimal,
    Field(ge=0, le=1, max_digits=4, decimal_places=3),
    DecimalAsNumber,
]
PreferenceScore = Annotated[
    Decimal,
    Field(ge=-1, le=2, max_digits=4, decimal_places=2),
    DecimalAsNumber,
]
RecommendationScore = Annotated[
    Decimal,
    Field(ge=0, le=1, max_digits=8, decimal_places=6),
    DecimalAsNumber,
]
NutritionValue = Annotated[
    Decimal,
    Field(ge=0, max_digits=10, decimal_places=2),
    DecimalAsNumber,
]


class ApiSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        hide_input_in_errors=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        validate_default=True,
    )


__all__ = [
    "ApiSchema",
    "AwareDatetime",
    "Month",
    "NormalizedScore",
    "NutritionValue",
    "PositiveId",
    "PreferenceScore",
    "RecommendationScore",
    "RefreshNumber",
]
