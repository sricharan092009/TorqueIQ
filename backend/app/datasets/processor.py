
import pandas as pd
import numpy as np

POWER_CONSTANT = 9549.2966


def process_engine_dataset(file_path: str):
    """
    Load and validate an engine performance CSV dataset.

    Required columns:
        rpm
        torque_nm

    Optional column:
        power_kw
    """

    try:
        df = pd.read_csv(file_path)
    except Exception as error:
        raise ValueError(f"Could not read CSV file: {error}")

    # Normalise column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Check required columns
    required_columns = ["rpm", "torque_nm"]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    # Convert measurements to numeric values
    for column in required_columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    # Remove rows with invalid measurements
    df = df.dropna(subset=required_columns)

    # Validate measurement values
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=required_columns)

    df = df[df["rpm"] > 0]

    if df.empty:
        raise ValueError(
            "No valid engine measurements found."
        )

    # Calculate power if the dataset does not contain it
    if "power_kw" not in df.columns:
        df["power_kw"] = (
            df["torque_nm"] * df["rpm"]
        ) / POWER_CONSTANT
    else:
        df["power_kw"] = pd.to_numeric(
            df["power_kw"], errors="coerce"
        )

        df = df.dropna(subset=["power_kw"])
        df = df[np.isfinite(df["power_kw"])]

    if df.empty:
        raise ValueError(
            "No valid power measurements found."
        )

    # Sort measurements by engine speed
    df = df.sort_values("rpm").reset_index(drop=True)

    # Return cleaned dataset information
    return {
        "total_records": len(df),
        "rpm_min": float(df["rpm"].min()),
        "rpm_max": float(df["rpm"].max()),
        "peak_torque_nm": float(df["torque_nm"].max()),
        "peak_power_kw": float(df["power_kw"].max()),
        "data": df.round(3).to_dict(orient="records")
    }
