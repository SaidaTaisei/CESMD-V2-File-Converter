from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .models import Metadata, WaveformRecord


def parse_v2_file(filepath: str) -> WaveformRecord:
    """V2ファイルを解析して WaveformRecord を返す。"""
    path = Path(filepath)
    with path.open("r") as f:
        content = f.readlines()

    metadata = Metadata.from_filepath(str(path))
    sampling_rate: float | None = None

    channel_num = 0
    for line in content[:30]:
        chan_match = re.search(r"Chan\s+(\d+)", line, re.IGNORECASE)
        if chan_match:
            channel_num = int(chan_match.group(1))
            metadata["channel_number"] = channel_num

        # 例: "(Sta Chn:  5)" や "(Sta Chn: 24)" を観測所通し番号として保持
        sta_chan_match = re.search(r"Sta\s*Chn\s*:\s*(\d+)", line, re.IGNORECASE)
        if sta_chan_match:
            metadata["station_channel_number"] = int(sta_chan_match.group(1))

        date_match = re.search(
            r"(?:Rcrd|Record)\s+of\s+([A-Za-z]+)\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{2,4})\s+(\d{1,2}):(\d{2}):\s*(\d{1,2}(?:\.\d+)?)",
            line,
            re.IGNORECASE,
        )
        if date_match:
            metadata["observation_time"] = date_match.group(0)
            metadata["obs_month"] = date_match.group(2)
            metadata["obs_day"] = int(date_match.group(3))
            metadata["obs_year"] = int(date_match.group(4))
            metadata["obs_hour"] = int(date_match.group(5))
            metadata["obs_minute"] = int(date_match.group(6))
            metadata["obs_second"] = float(date_match.group(7))
        else:
            earth_match = re.search(
                r"Earthquake\s+of\s+\w+\s+([A-Za-z]{3,})\s+(\d{1,2}),\s+(\d{4})\s+(\d{1,2}):(\d{2})(?::\s*(\d{1,2}(?:\.\d+)?))?\s+([A-Z]{2,4})",
                line,
                re.IGNORECASE,
            )
            if earth_match:
                metadata["observation_time"] = earth_match.group(0)
                metadata["obs_month"] = earth_match.group(1)
                metadata["obs_day"] = int(earth_match.group(2))
                metadata["obs_year"] = int(earth_match.group(3))
                metadata["obs_hour"] = int(earth_match.group(4))
                metadata["obs_minute"] = int(earth_match.group(5))
                sec_text = earth_match.group(6)
                metadata["obs_second"] = float(sec_text) if sec_text is not None else 0.0
                metadata["obs_timezone"] = earth_match.group(7).upper()

        utc_match = re.search(
            r"Start\s+time:\s+(\d{1,2})[/-](\d{1,2})[/-](\d{2,4}),\s+(\d{1,2}):(\d{2})(?::\s*(\d{1,2}(?:\.\d+)?))?\s+(UTC|GMT)(?:\s*\(.*?\))?",
            line,
            re.IGNORECASE,
        )
        if utc_match:
            metadata["utc_time"] = utc_match.group(0)
            metadata["utc_month"] = int(utc_match.group(1))
            metadata["utc_day"] = int(utc_match.group(2))
            year_text = utc_match.group(3)
            if len(year_text) == 2:
                year_2digit = int(year_text)
                full_year = 1900 + year_2digit if year_2digit >= 90 else 2000 + year_2digit
            else:
                full_year = int(year_text)
            metadata["utc_year"] = full_year
            metadata["utc_hour"] = int(utc_match.group(4))
            metadata["utc_minute"] = int(utc_match.group(5))
            sec_text = utc_match.group(6)
            metadata["utc_second"] = float(sec_text) if sec_text is not None else 0.0

        origin_match = re.search(
            r"\(ORIGIN(?:\([A-Z]+\))?:\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4}),\s*(\d{1,2}):(\d{2})(?::\s*(\d{1,2}(?:\.\d+)?))?\s+(UTC|GMT)\)",
            line,
            re.IGNORECASE,
        )
        if origin_match and not metadata.get("utc_time"):
            metadata["utc_time"] = origin_match.group(0)
            metadata["utc_month"] = int(origin_match.group(1))
            metadata["utc_day"] = int(origin_match.group(2))
            year_text = origin_match.group(3)
            if len(year_text) == 2:
                year_2digit = int(year_text)
                full_year = 1900 + year_2digit if year_2digit >= 90 else 2000 + year_2digit
            else:
                full_year = int(year_text)
            metadata["utc_year"] = full_year
            metadata["utc_hour"] = int(origin_match.group(4))
            metadata["utc_minute"] = int(origin_match.group(5))
            sec_text = origin_match.group(6)
            metadata["utc_second"] = float(sec_text) if sec_text is not None else 0.0

        if re.search(r"Station No\.", line, re.IGNORECASE):
            station_info = re.search(
                r"Station No\.\s+(\d+)\s+([\d\.]+)([NS])\s*,\s*([\d\.]+)([EW])",
                line,
                re.IGNORECASE,
            )
            if station_info:
                metadata["station_id"] = station_info.group(1)
                metadata["latitude"] = float(station_info.group(2)) * (1 if station_info.group(3) == "N" else -1)
                metadata["longitude"] = float(station_info.group(4)) * (1 if station_info.group(5) == "E" else -1)

        if re.search(r"Hypocenter:", line, re.IGNORECASE):
            metadata["hypocenter_info"] = line.strip()

        magnitude_match = re.search(r"ML:\s+(.+)", line, re.IGNORECASE)
        if magnitude_match:
            metadata["magnitude_info"] = magnitude_match.group(1)

        if re.search(r"Instr(ument)?\s+Period", line, re.IGNORECASE):
            period_info = re.search(r"Instr(ument)?\s+Period\s*=\s*([\d\.]+)\s*sec", line, re.IGNORECASE)
            if period_info:
                metadata["instrument_period"] = float(period_info.group(2))

        if re.search(r"At equally-spaced intervals of", line, re.IGNORECASE):
            interval_info = re.search(r"At equally-spaced intervals of\s*([\d\.]+)\s*sec", line, re.IGNORECASE)
            if interval_info:
                interval = float(interval_info.group(1))
                sampling_rate = 1.0 / interval
                metadata["sampling_rate"] = sampling_rate
                metadata["time_interval"] = interval

        if re.search(r"Peak acceleration", line, re.IGNORECASE):
            acc_info = re.search(r"Peak acceleration\s*=\s*([\d\.\-]+)", line, re.IGNORECASE)
            if acc_info:
                metadata["peak_acceleration"] = float(acc_info.group(1))

        if re.search(r"Peak\s+velocity", line, re.IGNORECASE):
            vel_info = re.search(r"Peak\s+velocity\s*=\s*([\d\.\-]+)", line, re.IGNORECASE)
            if vel_info:
                metadata["peak_velocity"] = float(vel_info.group(1))

        if re.search(r"Peak displacement", line, re.IGNORECASE):
            disp_info = re.search(r"Peak displacement\s*=\s*([\d\.\-]+)", line, re.IGNORECASE)
            if disp_info:
                metadata["peak_displacement"] = float(disp_info.group(1))

    if not metadata.get("utc_time") and not metadata.get("observation_time"):
        raise ValueError("日時が見つかりません")

    accel_start_line = None
    velocity_start_line = None
    displ_start_line = None
    end_of_data_line = None

    for i, line in enumerate(content):
        lower_line = line.lower()
        if "points of accel data equally spaced" in lower_line:
            accel_start_line = i + 1
        elif "points of veloc data equally spaced" in lower_line:
            velocity_start_line = i + 1
        elif "points of displ data equally spaced" in lower_line:
            displ_start_line = i + 1
        elif "end of data for channel" in lower_line:
            end_of_data_line = i

    if accel_start_line is None:
        raise ValueError("加速度データセクションが見つかりません")

    accel_end_line = velocity_start_line - 1 if velocity_start_line else end_of_data_line
    velocity_end_line = displ_start_line - 1 if displ_start_line else end_of_data_line
    displ_end_line = end_of_data_line

    acceleration_data: list[float] = []
    for i in range(accel_start_line, accel_end_line):
        try:
            line = content[i]
            values = [float(line[10 * j:10 * (j + 1)]) for j in range(8) if len(line[10 * j:10 + 10 * j]) > 3]
            acceleration_data.extend(values)
        except ValueError:
            pass
    acceleration = np.array(acceleration_data)

    velocity = None
    if velocity_start_line and velocity_end_line:
        velocity_data: list[float] = []
        for i in range(velocity_start_line, velocity_end_line):
            try:
                line = content[i]
                values = [float(line[10 * j:10 * (j + 1)]) for j in range(8) if len(line[10 * j:10 + 10 * j]) > 3]
                velocity_data.extend(values)
            except ValueError:
                pass
        velocity = np.array(velocity_data)

    displacement = None
    if displ_start_line and displ_end_line:
        displacement_data: list[float] = []
        for i in range(displ_start_line, displ_end_line):
            try:
                line = content[i]
                values = [float(line[10 * j:10 * (j + 1)]) for j in range(8) if len(line[10 * j:10 + 10 * j]) > 3]
                displacement_data.extend(values)
            except ValueError:
                pass
        displacement = np.array(displacement_data)

    time_array = None
    if sampling_rate is not None:
        dt = 1.0 / sampling_rate
        n = len(acceleration)
        time_array = np.arange(0, n * dt, dt)[:n]

    return WaveformRecord(
        time=time_array,
        acceleration=acceleration,
        velocity=velocity,
        displacement=displacement,
        metadata=metadata,
    )
