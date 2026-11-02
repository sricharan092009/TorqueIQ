"""
TorqueIQ - Engine Diagnostics
Explainable rule-based engine analysis.
"""

from typing import Any


def analyze_engine_data(dataset: list[dict[str, Any]]) -> dict:

    if not dataset:
        raise ValueError("Engine dataset is empty.")

    required = {"rpm", "torque_nm", "power_kw"}
    rows = []

    for index, row in enumerate(dataset):
        if not required.issubset(row):
            raise ValueError(
                f"Record {index + 1} is missing required columns."
            )

        try:
            rpm = float(row["rpm"])
            torque = float(row["torque_nm"])
            power = float(row["power_kw"])
        except (TypeError, ValueError):
            raise ValueError(
                f"Record {index + 1} contains invalid measurements."
            )

        if rpm <= 0 or torque < 0 or power < 0:
            raise ValueError(
                f"Record {index + 1} contains invalid values."
            )

        rows.append({
            "rpm": rpm,
            "torque_nm": torque,
            "power_kw": power
        })

    rows.sort(key=lambda item: item["rpm"])

    findings = []

    peak_torque_row = max(
        rows, key=lambda item: item["torque_nm"]
    )

    peak_power_row = max(
        rows, key=lambda item: item["power_kw"]
    )

    highest_rpm_row = rows[-1]

    peak_torque = peak_torque_row["torque_nm"]
    torque_at_max_rpm = highest_rpm_row["torque_nm"]

    # RULE 1: Torque drop

    if peak_torque > 0:
        torque_drop = (
            (peak_torque - torque_at_max_rpm)
            / peak_torque
        ) * 100
    else:
        torque_drop = 0.0

    if torque_drop >= 20:
        findings.append({
            "code": "TORQUE_DROP",
            "severity": "warning",
            "title": "Significant torque reduction",
            "description": (
                f"Torque is {torque_drop:.1f}% below its peak "
                "at the highest measured RPM."
            ),
            "recommendation": (
                "Review the torque curve and compare it with "
                "the engine's expected operating characteristics."
            )
        })

    # RULE 2: Torque fluctuations

    for previous, current in zip(rows, rows[1:]):

        previous_torque = previous["torque_nm"]

        if previous_torque <= 0:
            continue

        change = (
            (current["torque_nm"] - previous_torque)
            / previous_torque
        ) * 100

        if abs(change) >= 20:
            findings.append({
                "code": "TORQUE_FLUCTUATION",
                "severity": "warning",
                "title": "Large torque variation",
                "description": (
                    f"Torque changes by {change:.1f}% between "
                    f"{previous['rpm']:.0f} and {current['rpm']:.0f} RPM."
                ),
                "recommendation": (
                    "Check measurement consistency and collect "
                    "additional RPM measurements."
                )
            })

    # RULE 3: Power consistency

    for row in rows:

        expected_power = (
            row["torque_nm"] * row["rpm"]
        ) / 9549.2966

        if expected_power > 0:

            difference = (
                abs(row["power_kw"] - expected_power)
                / expected_power
            ) * 100

            if difference > 5:
                findings.append({
                    "code": "POWER_MISMATCH",
                    "severity": "warning",
                    "title": "Power measurement mismatch",
                    "description": (
                        f"Recorded power differs from calculated "
                        f"power by {difference:.1f}% at "
                        f"{row['rpm']:.0f} RPM."
                    ),
                    "recommendation": (
                        "Verify measurement units and data accuracy."
                    )
                })

    if not findings:
        findings.append({
            "code": "NO_RULE_TRIGGERED",
            "severity": "info",
            "title": "No unusual patterns detected",
            "description": (
                "The measurements did not trigger the current "
                "diagnostic rules."
            ),
            "recommendation": (
                "Continue collecting measurements across the "
                "engine's operating range."
            )
        })

    return {
        "diagnostic_engine": "TorqueIQ Rule-Based Diagnostics",
        "analysis_type": "Rule-based",
        "records_analysed": len(rows),
        "peak_torque_nm": round(peak_torque, 2),
        "peak_torque_rpm": peak_torque_row["rpm"],
        "peak_power_kw": round(
            peak_power_row["power_kw"], 2
        ),
        "peak_power_rpm": peak_power_row["rpm"],
        "torque_drop_percent": round(torque_drop, 2),
        "findings_count": len(findings),
        "findings": findings,
        "limitations": (
            "These findings identify data patterns, not confirmed "
            "mechanical faults."
        )
    }
