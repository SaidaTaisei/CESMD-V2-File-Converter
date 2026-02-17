# CESMD V2 File Converter

*[日本語](README_JP.md)*

A simple GUI tool for converting V2 format files from the Center for Engineering Strong Motion Data (CESMD) to CSV, MAT, and HDF5 formats.

## Features

- Direct extraction of acceleration, velocity, and displacement data from V2 files
- Conversion to CSV, MAT (MATLAB), and HDF5 formats
- User-friendly graphical interface
- Batch processing of multiple V2 files in a folder
- Drag and drop functionality for input/output folder selection (if tkinterdnd2 is installed)
- Automatic splitting of V2 files containing multiple channels
- Custom icons (if Pillow is installed)

## Quick Start (Prebuilt Windows Executable)

You can use the prebuilt Windows executable from the GitHub Release page:

- Download URL: [CESMD-Converter.exe](https://github.com/SaidaTaisei/CESMD-V2-File-Converter/releases/download/v0.2.0/CESMD-Converter.exe)

After downloading, run the `.exe` file directly.

## Dependencies

This tool requires the following libraries:

* numpy>=1.20.0
* pandas>=1.3.0
* scipy>=1.7.0
* h5py>=3.1.0
* matplotlib>=3.4.0
* Pillow>=9.0.0 (optional, required for icon display)
* tkinterdnd2>=0.3.0 (optional, required for drag and drop functionality)

You can install the required libraries with the following command:

```bash
pip install -r requirements.txt
```

## How Data Extraction Works

This converter directly extracts the following data from V2 files:

- Acceleration data (from the "points of accel data" section)
- Velocity data (from the "points of veloc data" section, if present)
- Displacement data (from the "points of displ data" section, if present)
- Metadata (from the file header)

V2 files already contain acceleration, velocity, and displacement data, and this tool extracts them and converts them to the specified format. It does not perform integration calculations.

## Installation

### Requirements

- Python 3.8 or higher
- Required packages (listed in requirements.txt)

### Setup

1. Clone or download the repository
   ```
   git clone https://github.com/yourusername/cesmd_converter.git
   cd cesmd_converter
   ```

2. Install the required packages
   ```
   pip install -r requirements.txt
   ```

## How to Use

1. Run the script
   ```
   python converter.py
   ```

2. In the GUI, perform the following operations
   - Select the input directory containing V2 files (drag and drop also possible)
   - Select the output directory for the converted files (drag and drop also possible)
   - Choose an output format: CSV, MAT, or HDF5
   - Click the "Convert" button

3. When the conversion process is complete, the results will be displayed

## Library Usage

You can also use this project as a Python library.

```python
from cesmd_converter import parse_v2_file, to_csv, to_mat, to_hdf5

record = parse_v2_file("CHAN001.V2")
print(record.metadata.station_id)
print(record.acceleration[:5])

to_csv(record, "channel_1.csv")
to_mat(record, "channel_1.mat")
to_hdf5(record, "channel_1.h5")
```

## Output File Structure

### CSV Format
- Metadata as comments
- Columns: Time, Acceleration, Velocity (if present), Displacement (if present)

### MAT Format
- time: time array
- acceleration: acceleration data
- velocity: velocity data (if present in the V2 file)
- displacement: displacement data (if present in the V2 file)
- metadata: metadata structure

### HDF5 Format
- /time: time dataset
- /acceleration: acceleration dataset
- /velocity: velocity dataset (if present in the V2 file)
- /displacement: displacement dataset (if present in the V2 file)
- /metadata: metadata group (stored as attributes with key-value pairs)

## Processing Files with Multiple Channels

This tool automatically detects V2 files containing multiple channels and splits them for processing by channel. This allows each channel's data to be output as an individual file.

## Notes

- Only V2 files are supported
- Not all V2 files contain velocity and displacement data
- Some metadata may be lost depending on the output format

## License

MIT License 