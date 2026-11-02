
import os
import uuid
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.datasets.processor import process_engine_dataset
from app.services.diagnostics import analyze_engine_data


logger = logging.getLogger("torqueiq.datasets")

router = APIRouter(
    prefix="/api/datasets",
    tags=["Datasets"]
)

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../datasets/raw")
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024


# CSV VALIDATION

async def read_csv_upload(file: UploadFile):
    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported."
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded CSV file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum upload size is 10 MB."
        )

    return content


# ENGINE METRICS

def calculate_metrics(dataset):
    if not dataset:
        raise ValueError("No valid engine measurements found.")

    peak_torque = max(
        dataset,
        key=lambda row: float(row["torque_nm"])
    )

    peak_power = max(
        dataset,
        key=lambda row: float(row["power_kw"])
    )

    torque_values = [
        float(row["torque_nm"]) for row in dataset
    ]

    power_values = [
        float(row["power_kw"]) for row in dataset
    ]

    rpm_values = [
        float(row["rpm"]) for row in dataset
    ]

    return {
        "records": len(dataset),
        "rpm_min": min(rpm_values),
        "rpm_max": max(rpm_values),

        "average_torque_nm": round(
            sum(torque_values) / len(torque_values), 2
        ),

        "average_power_kw": round(
            sum(power_values) / len(power_values), 2
        ),

        "peak_torque_nm": float(peak_torque["torque_nm"]),
        "peak_torque_rpm": float(peak_torque["rpm"]),

        "peak_power_kw": float(peak_power["power_kw"]),
        "peak_power_rpm": float(peak_power["rpm"]),

        "torque_range_nm": round(
            max(torque_values) - min(torque_values), 2
        ),

        "power_range_kw": round(
            max(power_values) - min(power_values), 2
        )
    }


# PERCENTAGE DIFFERENCE

def percentage_difference(value_a, value_b):
    if value_a == 0:
        return None

    return round(
        ((value_b - value_a) / value_a) * 100,
        2
    )


# PROCESS TEMPORARY CSV

def process_csv_bytes(content):
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".csv",
            delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        return process_engine_dataset(temp_path)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# 1. DATASET UPLOAD

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    file_path = os.path.join(
        UPLOAD_DIR,
        f"{uuid.uuid4().hex}.csv"
    )

    try:
        content = await read_csv_upload(file)

        with open(file_path, "wb") as saved_file:
            saved_file.write(content)

        result = process_engine_dataset(file_path)

        return {
            "message": "Dataset uploaded and processed successfully.",
            "filename": file.filename,
            "records": result["total_records"],
            "rpm_min": result["rpm_min"],
            "rpm_max": result["rpm_max"],
            "peak_torque_nm": result["peak_torque_nm"],
            "peak_power_kw": result["peak_power_kw"],
            "data": result["data"]
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        logger.exception("Dataset upload failed")

        raise HTTPException(
            status_code=500,
            detail=f"Dataset upload failed: {type(error).__name__}: {error}"
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# 2. ENGINE COMPARISON

@router.post("/compare")
async def compare_engine_datasets(
    engine_a: UploadFile = File(...),
    engine_b: UploadFile = File(...)
):
    try:
        content_a = await read_csv_upload(engine_a)
        content_b = await read_csv_upload(engine_b)

        result_a = process_csv_bytes(content_a)
        result_b = process_csv_bytes(content_b)

        data_a = result_a["data"]
        data_b = result_b["data"]

        metrics_a = calculate_metrics(data_a)
        metrics_b = calculate_metrics(data_b)

        return {
            "message": "Engine datasets compared successfully.",

            "engine_a": {
                "filename": engine_a.filename,
                "metrics": metrics_a,
                "data": data_a
            },

            "engine_b": {
                "filename": engine_b.filename,
                "metrics": metrics_b,
                "data": data_b
            },

            "comparison": {
                "peak_torque_difference_percent":
                    percentage_difference(
                        metrics_a["peak_torque_nm"],
                        metrics_b["peak_torque_nm"]
                    ),

                "peak_power_difference_percent":
                    percentage_difference(
                        metrics_a["peak_power_kw"],
                        metrics_b["peak_power_kw"]
                    )
            }
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        logger.exception("Engine comparison failed")

        raise HTTPException(
            status_code=500,
            detail=f"Engine comparison failed: {type(error).__name__}: {error}"
        )


# 3. ADVANCED ENGINE ANALYSIS

@router.post("/analyze")
async def analyze_engine_dataset(file: UploadFile = File(...)):
    try:
        content = await read_csv_upload(file)

        result = process_csv_bytes(content)
        data = result["data"]

        metrics = calculate_metrics(data)

        peak_torque = max(
            data,
            key=lambda row: float(row["torque_nm"])
        )

        highest_rpm_row = max(
            data,
            key=lambda row: float(row["rpm"])
        )

        peak_torque_value = float(peak_torque["torque_nm"])
        torque_at_max_rpm = float(highest_rpm_row["torque_nm"])

        if peak_torque_value > 0:
            torque_drop = (
                (peak_torque_value - torque_at_max_rpm)
                / peak_torque_value
            ) * 100
        else:
            torque_drop = 0.0

        metrics["torque_drop_at_max_rpm_percent"] = round(
            torque_drop, 2
        )

        metrics["rpm_range"] = {
            "minimum": metrics["rpm_min"],
            "maximum": metrics["rpm_max"]
        }

        return {
            "message": "Advanced engine analysis completed successfully.",
            "filename": file.filename,
            "metrics": metrics,
            "data": data
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        logger.exception("Advanced engine analysis failed")

        raise HTTPException(
            status_code=500,
            detail=f"Advanced engine analysis failed: {type(error).__name__}: {error}"
        )
