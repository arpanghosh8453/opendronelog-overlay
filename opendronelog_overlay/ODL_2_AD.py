#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AIRDATA_HEADERS = [
    "time(millisecond)",
    "datetime(utc)",
    "latitude",
    "longitude",
    "height_above_takeoff(meters)",
    "height_above_ground_at_drone_location(meters)",
    "ground_elevation_at_drone_location(meters)",
    "altitude_above_seaLevel(meters)",
    "height_sonar(meters)",
    "speed(m/s)",
    "distance(meters)",
    "mileage(meters)",
    "satellites",
    "gpslevel",
    "voltage(v)",
    "max_altitude(meters)",
    "max_ascent(meters)",
    "max_speed(m/s)",
    "max_distance(meters)",
    " xSpeed(m/s)",
    " ySpeed(m/s)",
    " zSpeed(m/s)",
    " compass_heading(degrees)",
    " pitch(degrees)",
    " roll(degrees)",
    "isPhoto",
    "isVideo",
    "rc_elevator",
    "rc_aileron",
    "rc_throttle",
    "rc_rudder",
    "rc_elevator(percent)",
    "rc_aileron(percent)",
    "rc_throttle(percent)",
    "rc_rudder(percent)",
    "gimbal_heading(degrees)",
    "gimbal_pitch(degrees)",
    "gimbal_roll(degrees)",
    "battery_percent",
    "voltageCell1",
    "voltageCell2",
    "voltageCell3",
    "voltageCell4",
    "voltageCell5",
    "voltageCell6",
    "current(A)",
    "battery_temperature(c)",
    "altitude(meters)",
    "ascent(meters)",
    "flycStateRaw",
    "flycState",
    "message",
]


def _f(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _i_from_float(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(round(value)))


def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_start_time(rows: list[dict[str, str]]) -> datetime | None:
    for row in rows:
        raw_meta = (row.get("metadata") or "").strip()
        if not raw_meta:
            continue
        try:
            meta = json.loads(raw_meta)
        except json.JSONDecodeError:
            continue
        start_time = meta.get("start_time") if isinstance(meta, dict) else None
        if not start_time:
            continue
        try:
            dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _extract_cell_voltages(cell_text: str) -> list[str]:
    text = (cell_text or "").strip()
    if not text:
        return [""] * 6
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return [""] * 6
    if not isinstance(parsed, (list, tuple)):
        return [""] * 6
    out = [""] * 6
    for i, value in enumerate(parsed[:6]):
        fv = _f(value)
        out[i] = "" if fv is None else f"{fv:.3f}".rstrip("0").rstrip(".")
    return out


def _fmt_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _pick_numeric_metric(row: dict[str, str], metric_col: str, imperial_col: str, factor: float) -> float | None:
    metric_val = _f(row.get(metric_col))
    if metric_val is not None:
        return metric_val
    imperial_val = _f(row.get(imperial_col))
    if imperial_val is None:
        return None
    return imperial_val * factor


def _pick_temp_c(row: dict[str, str], c_col: str, f_col: str) -> float | None:
    temp_c = _f(row.get(c_col))
    if temp_c is not None:
        return temp_c
    temp_f = _f(row.get(f_col))
    if temp_f is None:
        return None
    return (temp_f - 32.0) * (5.0 / 9.0)


def _first_numeric(row: dict[str, str], columns: list[str]) -> float | None:
    for col in columns:
        value = _f(row.get(col))
        if value is not None:
            return value
    return None


def convert_odl_to_airdata(input_csv: Path, output_csv: Path) -> None:
    with input_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Input CSV has no data rows")

    start_dt = _parse_start_time(rows)

    mileage_m = 0.0
    prev_lat: float | None = None
    prev_lon: float | None = None
    max_altitude = float("-inf")
    max_ascent = float("-inf")
    max_speed = float("-inf")
    max_distance = float("-inf")
    prev_height: float | None = None
    prev_time_s: float | None = None

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AIRDATA_HEADERS)
        writer.writeheader()

        for row in rows:
            time_s = _f(row.get("time_s"))
            lat = _f(row.get("lat"))
            lon = _f(row.get("lng"))
            height = _pick_numeric_metric(row, "height_m", "height_ft", 0.3048)
            vps_height = _pick_numeric_metric(row, "vps_height_m", "vps_height_ft", 0.3048)
            altitude = _pick_numeric_metric(row, "altitude_m", "altitude_ft", 0.3048)
            speed = _pick_numeric_metric(row, "speed_ms", "speed_mph", 0.44704)
            distance = _pick_numeric_metric(row, "distance_to_home_m", "distance_to_home_ft", 0.3048)
            satellites = _f(row.get("satellites"))
            battery_voltage = _f(row.get("battery_voltage_v"))
            battery_percent = _f(row.get("battery_percent"))
            battery_temp = _pick_temp_c(row, "battery_temp_c", "battery_temp_f")
            x_speed = _pick_numeric_metric(row, "velocity_x_ms", "velocity_x_mph", 0.44704)
            y_speed = _pick_numeric_metric(row, "velocity_y_ms", "velocity_y_mph", 0.44704)
            z_speed = _pick_numeric_metric(row, "velocity_z_ms", "velocity_z_mph", 0.44704)
            pitch = _f(row.get("pitch_deg"))
            roll = _f(row.get("roll_deg"))
            yaw = _f(row.get("yaw_deg"))
            gimbal_pitch = _first_numeric(
                row,
                ["gimbal_pitch_deg", "gimbal_pitch", "gimbal_pitch(deg)"],
            )
            gimbal_roll = _first_numeric(
                row,
                ["gimbal_roll_deg", "gimbal_roll", "gimbal_roll(deg)"],
            )
            gimbal_yaw = _first_numeric(
                row,
                ["gimbal_yaw_deg", "gimbal_heading_deg", "gimbal_yaw", "gimbal_heading"],
            )

            if lat is not None and lon is not None and prev_lat is not None and prev_lon is not None:
                mileage_m += _haversine_m(prev_lat, prev_lon, lat, lon)
            if lat is not None and lon is not None:
                prev_lat, prev_lon = lat, lon

            ascent = None
            if prev_height is not None and height is not None and prev_time_s is not None and time_s is not None:
                dt = time_s - prev_time_s
                if dt > 0:
                    ascent = (height - prev_height) / dt
            if height is not None:
                prev_height = height
            if time_s is not None:
                prev_time_s = time_s

            if altitude is not None:
                max_altitude = max(max_altitude, altitude)
            if ascent is not None:
                max_ascent = max(max_ascent, ascent)
            if speed is not None:
                max_speed = max(max_speed, speed)
            if distance is not None:
                max_distance = max(max_distance, distance)

            heading = None if yaw is None else (yaw % 360.0 + 360.0) % 360.0
            gimbal_heading = None if gimbal_yaw is None else (gimbal_yaw % 360.0 + 360.0) % 360.0

            dt_text = ""
            if start_dt is not None and time_s is not None:
                dt_text = (start_dt + timedelta(seconds=time_s)).strftime("%Y-%m-%d %H:%M:%S")

            cells = _extract_cell_voltages(row.get("cell_voltages", ""))

            out_row = {header: "" for header in AIRDATA_HEADERS}
            out_row["time(millisecond)"] = _i_from_float(None if time_s is None else time_s * 1000.0)
            out_row["datetime(utc)"] = dt_text
            out_row["latitude"] = _fmt_float(lat, 15)
            out_row["longitude"] = _fmt_float(lon, 15)
            out_row["height_above_takeoff(meters)"] = _fmt_float(height)
            out_row["height_above_ground_at_drone_location(meters)"] = _fmt_float(vps_height)
            out_row["altitude_above_seaLevel(meters)"] = _fmt_float(altitude)
            out_row["height_sonar(meters)"] = _fmt_float(vps_height)
            out_row["speed(m/s)"] = _fmt_float(speed)
            out_row["distance(meters)"] = _fmt_float(distance)
            out_row["mileage(meters)"] = _fmt_float(mileage_m)
            out_row["satellites"] = _i_from_float(satellites)
            out_row["voltage(v)"] = _fmt_float(battery_voltage, 3)
            out_row["max_altitude(meters)"] = "" if max_altitude == float("-inf") else _fmt_float(max_altitude)
            out_row["max_ascent(meters)"] = "" if max_ascent == float("-inf") else _fmt_float(max_ascent)
            out_row["max_speed(m/s)"] = "" if max_speed == float("-inf") else _fmt_float(max_speed)
            out_row["max_distance(meters)"] = "" if max_distance == float("-inf") else _fmt_float(max_distance)
            out_row[" xSpeed(m/s)"] = _fmt_float(x_speed)
            out_row[" ySpeed(m/s)"] = _fmt_float(y_speed)
            out_row[" zSpeed(m/s)"] = _fmt_float(z_speed)
            out_row[" compass_heading(degrees)"] = _fmt_float(heading, 1)
            out_row[" pitch(degrees)"] = _fmt_float(pitch, 1)
            out_row[" roll(degrees)"] = _fmt_float(roll, 1)
            out_row["isPhoto"] = _i_from_float(_f(row.get("is_photo")))
            out_row["isVideo"] = _i_from_float(_f(row.get("is_video")))
            out_row["rc_elevator"] = _s(row.get("rc_elevator", ""))
            out_row["rc_aileron"] = _s(row.get("rc_aileron", ""))
            out_row["rc_throttle"] = _s(row.get("rc_throttle", ""))
            out_row["rc_rudder"] = _s(row.get("rc_rudder", ""))
            out_row["rc_elevator(percent)"] = _s(row.get("rc_elevator", ""))
            out_row["rc_aileron(percent)"] = _s(row.get("rc_aileron", ""))
            out_row["rc_throttle(percent)"] = _s(row.get("rc_throttle", ""))
            out_row["rc_rudder(percent)"] = _s(row.get("rc_rudder", ""))
            out_row["gimbal_heading(degrees)"] = _fmt_float(gimbal_heading, 1)
            out_row["gimbal_pitch(degrees)"] = _fmt_float(gimbal_pitch, 1)
            out_row["gimbal_roll(degrees)"] = _fmt_float(gimbal_roll, 1)
            out_row["battery_percent"] = _i_from_float(battery_percent)
            out_row["voltageCell1"] = cells[0]
            out_row["voltageCell2"] = cells[1]
            out_row["voltageCell3"] = cells[2]
            out_row["voltageCell4"] = cells[3]
            out_row["voltageCell5"] = cells[4]
            out_row["voltageCell6"] = cells[5]
            out_row["battery_temperature(c)"] = _fmt_float(battery_temp, 1)
            out_row["altitude(meters)"] = _fmt_float(altitude)
            out_row["ascent(meters)"] = _fmt_float(ascent)
            out_row["flycState"] = _s(row.get("flight_mode", ""))
            out_row["message"] = _s(row.get("messages", ""))

            writer.writerow(out_row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert OpenDroneLog CSV to Airdata-like CSV format while preserving all Airdata headers."
    )
    parser.add_argument("input_csv", type=Path, help="Path to OpenDroneLog CSV")
    parser.add_argument("output_csv", type=Path, help="Path to output Airdata-format CSV")
    args = parser.parse_args()

    convert_odl_to_airdata(args.input_csv, args.output_csv)


if __name__ == "__main__":
    main()
