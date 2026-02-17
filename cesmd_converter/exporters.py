from __future__ import annotations

import h5py
from scipy import io as sio

from .models import WaveformRecord


def to_csv(record: WaveformRecord, output_path: str) -> bool:
    """WaveformRecord をCSV形式で保存する。"""
    if not record.has_required_data():
        raise ValueError("データがロードされていません")
    length_check = record.validate_lengths()

    metadata_dict = record.metadata.to_flat_dict(include_none=False)
    metadata_items = []
    for key, value in metadata_dict.items():
        if isinstance(value, float):
            metadata_items.append(f"{key}: {value:.16g}")
        else:
            metadata_items.append(f"{key}: {value}")
    metadata_str = "# " + ", ".join(metadata_items)

    with open(output_path, "w") as f:
        f.write(metadata_str + "\n")

        columns = ["Time", "Acceleration"]
        if length_check["velocity"]:
            columns.append("Velocity")
        elif record.velocity is not None:
            print(f"警告: 速度データの長さが時間配列と一致しません。({len(record.velocity)} != {len(record.time)})")

        if length_check["displacement"]:
            columns.append("Displacement")
        elif record.displacement is not None:
            print(f"警告: 変位データの長さが時間配列と一致しません。({len(record.displacement)} != {len(record.time)})")

        f.write(",".join(columns) + "\n")

        for i in range(len(record.time)):
            row = [str(record.time[i]), str(record.acceleration[i])]
            if "Velocity" in columns:
                row.append(str(record.velocity[i]))
            if "Displacement" in columns:
                row.append(str(record.displacement[i]))
            f.write(",".join(row) + "\n")

    return True


def to_mat(record: WaveformRecord, output_path: str) -> bool:
    """WaveformRecord をMAT形式で保存する。"""
    sio.savemat(output_path, record.to_mat_dict())
    return True


def to_hdf5(record: WaveformRecord, output_path: str) -> bool:
    """WaveformRecord をHDF5形式で保存する。"""
    if not record.has_required_data():
        raise ValueError("データがロードされていません")
    with h5py.File(output_path, "w") as h5f:
        record.write_hdf5(h5f)
    return True
