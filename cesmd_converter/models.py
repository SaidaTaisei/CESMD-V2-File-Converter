from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Any, Iterator

import h5py
import numpy as np


@dataclass
class Metadata:
    """V2ファイルから抽出したメタデータを保持する"""

    filename: str = ""
    filepath: str = ""
    utc_time: str | None = None
    observation_time: str | None = None
    channel_number: int | None = None
    station_channel_number: int | None = None
    obs_month: str | None = None
    obs_day: int | None = None
    obs_year: int | None = None
    obs_hour: int | None = None
    obs_minute: int | None = None
    obs_second: float | None = None
    obs_timezone: str | None = None
    utc_month: int | None = None
    utc_day: int | None = None
    utc_year: int | None = None
    utc_hour: int | None = None
    utc_minute: int | None = None
    utc_second: float | None = None
    station_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    hypocenter_info: str | None = None
    magnitude_info: str | None = None
    instrument_period: float | None = None
    sampling_rate: float | None = None
    time_interval: float | None = None
    peak_acceleration: float | None = None
    peak_velocity: float | None = None
    peak_displacement: float | None = None
    extras: dict[str, int | float | str | None] = field(default_factory=dict)

    @classmethod
    def from_filepath(cls, filepath: str) -> "Metadata":
        return cls(filename=os.path.basename(filepath), filepath=filepath)

    @staticmethod
    def _known_field_names() -> set[str]:
        return {f.name for f in fields(Metadata) if f.name != "extras"}

    def __getitem__(self, key: str) -> Any:
        if key in self._known_field_names():
            return getattr(self, key)
        return self.extras[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self._known_field_names():
            setattr(self, key, value)
        else:
            self.extras[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._known_field_names():
            value = getattr(self, key)
            return default if value is None else value
        return self.extras.get(key, default)

    def to_flat_dict(self, include_none: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in self._known_field_names():
            value = getattr(self, name)
            if include_none or value is not None:
                result[name] = value
        for key, value in self.extras.items():
            if include_none or value is not None:
                result[key] = value
        return result

    def items(self) -> Iterator[tuple[str, Any]]:
        return iter(self.to_flat_dict(include_none=True).items())


@dataclass
class WaveformRecord:
    """波形データとメタデータを1レコードとして保持する"""

    time: np.ndarray | None = None
    acceleration: np.ndarray | None = None
    velocity: np.ndarray | None = None
    displacement: np.ndarray | None = None
    metadata: Metadata = field(default_factory=Metadata)

    def has_required_data(self) -> bool:
        return self.time is not None and self.acceleration is not None

    def validate_lengths(self) -> dict[str, bool]:
        if self.time is None:
            return {"velocity": False, "displacement": False}
        return {
            "velocity": self.velocity is not None and len(self.velocity) == len(self.time),
            "displacement": self.displacement is not None and len(self.displacement) == len(self.time),
        }

    def to_mat_dict(self) -> dict[str, Any]:
        if not self.has_required_data():
            raise ValueError("データがロードされていません")

        mat_dict: dict[str, Any] = {
            "time": self.time,
            "acceleration": self.acceleration,
            "metadata": self.metadata.to_flat_dict(include_none=False),
        }
        if self.velocity is not None:
            mat_dict["velocity"] = self.velocity
        if self.displacement is not None:
            mat_dict["displacement"] = self.displacement
        return mat_dict

    def write_hdf5(self, h5f: h5py.File) -> None:
        if not self.has_required_data():
            raise ValueError("データがロードされていません")

        h5f.create_dataset("time", data=self.time)
        h5f.create_dataset("acceleration", data=self.acceleration)

        if self.velocity is not None:
            h5f.create_dataset("velocity", data=self.velocity)
        if self.displacement is not None:
            h5f.create_dataset("displacement", data=self.displacement)

        meta_group = h5f.create_group("metadata")
        metadata_dict = self.metadata.to_flat_dict(include_none=False)
        for key, value in metadata_dict.items():
            if isinstance(value, (int, float, str)):
                meta_group.attrs[key] = value
