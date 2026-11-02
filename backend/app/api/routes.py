
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.calculations.engine import (
    calculate_engine_performance,
    generate_performance_curve
)

# Create API router
router = APIRouter(
    prefix="/api/engine",
    tags=["Engine"]
)


class EngineInput(BaseModel):
    torque_nm: float = Field(gt=0, le=10000)
    rpm: int = Field(gt=0, le=30000)


class CurveInput(BaseModel):
    torque_nm: float = Field(gt=0, le=10000)
    start_rpm: int = Field(gt=0, le=30000)
    end_rpm: int = Field(gt=0, le=30000)
    step: int = Field(default=500, gt=0, le=10000)


@router.post("/calculate")
def calculate_engine(data: EngineInput):
    try:
        return calculate_engine_performance(
            data.torque_nm,
            data.rpm
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.post("/curve")
def engine_curve(data: CurveInput):
    try:
        return {
            "curve": generate_performance_curve(
                data.torque_nm,
                data.start_rpm,
                data.end_rpm,
                data.step
            )
        }
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
