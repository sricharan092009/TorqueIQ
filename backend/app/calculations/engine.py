
import math


# ==========================================
# TORQUEIQ - ENGINE CALCULATION ENGINE
# ==========================================

KW_TO_HP = 1.34102209
POWER_CONSTANT = 9549.2966


def validate_inputs(torque_nm: float, rpm: int):
    """Validate engine torque and RPM inputs."""

    if not isinstance(torque_nm, (int, float)):
        raise ValueError("Torque must be a number.")

    if isinstance(torque_nm, bool) or not math.isfinite(torque_nm):
        raise ValueError("Torque must be a finite number.")

    if torque_nm <= 0:
        raise ValueError("Torque must be greater than zero.")

    if isinstance(rpm, bool) or not isinstance(rpm, int):
        raise ValueError("RPM must be an integer.")

    if rpm <= 0:
        raise ValueError("RPM must be greater than zero.")


def calculate_engine_performance(
    torque_nm: float,
    rpm: int
):
    """
    Calculate engine power and horsepower.

    Power (kW) = Torque x RPM / 9549.2966
    """

    validate_inputs(torque_nm, rpm)

    power_kw = (torque_nm * rpm) / POWER_CONSTANT
    horsepower = power_kw * KW_TO_HP

    return {
        "torque_nm": round(torque_nm, 2),
        "rpm": rpm,
        "power_kw": round(power_kw, 2),
        "power_hp": round(horsepower, 2)
    }


def generate_performance_curve(
    torque_nm: float,
    start_rpm: int,
    end_rpm: int,
    step: int = 500
):
    """
    Generate illustrative performance points
    assuming constant torque across the RPM range.

    Actual engine curves will later use measured
    torque data from engine datasets.
    """

    validate_inputs(torque_nm, start_rpm)

    if isinstance(end_rpm, bool) or not isinstance(end_rpm, int):
        raise ValueError("End RPM must be an integer.")

    if isinstance(step, bool) or not isinstance(step, int):
        raise ValueError("Step must be an integer.")

    if end_rpm < start_rpm:
        raise ValueError("End RPM must be >= start RPM.")

    if end_rpm > 30000:
        raise ValueError("End RPM exceeds the supported limit.")

    if step <= 0:
        raise ValueError("Step must be greater than zero.")

    if (end_rpm - start_rpm) // step > 1000:
        raise ValueError("Too many data points requested.")

    curve = []

    for rpm in range(start_rpm, end_rpm + 1, step):

        performance = calculate_engine_performance(
            torque_nm,
            rpm
        )

        curve.append(performance)

    return curve
