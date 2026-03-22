# OpenDroneLog Overlay

Configurable drone telemetry card overlay for video exports.

## Why this stack

- `opencv-python`: Fast frame I/O + drawing, practical for near real-time rendering on all major OSes.
- `polars`: Robust and fast CSV ingestion for large telemetry exports.
- `PyYAML`: Simple user-editable config file support.
- `typer`: Clean CLI interface.
- `numpy`: Fast interpolation of telemetry to video timestamps.

This combination is reliable and easier to ship than browser pipelines for an offline CLI workflow.

## Install

```bash
git clone https://github.com/arpanghosh8453/opendronelog-overlay.git
cd opendronelog-overlay
pip install -e .
```

## Run

Generate transparent alpha overlay clip:

```bash
opendronelog-overlay \
  --input-csv ./csv/FlightRecord_2026-03-17_11-22-12_.csv \
  --config ./examples/overlay.config.yaml \
  --output-video ./out/overlay-alpha.mov \
  -v
```

Generate SRT subtitles with selected telemetry:

```bash
opendronelog-overlay \
  --input-csv ./csv/FlightRecord_2026-03-17_11-22-12_.csv \
  --config ./examples/overlay.config.yaml \
  --output-video ./out/overlay-alpha.mov \
  --output-srt ./out/overlay-telemetry.srt \
  -v
```

Maximum logs (including ffmpeg info in transparent mode):

```bash
opendronelog-overlay \
  --input-csv ./csv/FlightRecord_2026-03-17_11-22-12_.csv \
  --config ./examples/overlay.config.yaml \
  --output-video ./out/overlay-alpha.mov \
  -vv
```

Progress bar controls:

- default: progress bar enabled
- disable: `--no-progress`
- enable explicitly: `--progress`

## Config

See `examples/overlay.config.yaml`.

- `telemetry.include`: choose which fields appear on the card and in SRT output.
- `telemetry.unit_system`: `auto`, `metric`, or `imperial`.
- `rc_sticks.enabled`: toggle mini joystick visualizer.
- `transparent_output.*`: canvas/fps/codec for alpha clip output mode.
- `style.panel_bg_hex`: background box color, for example `#1E2434`.
- `style.label_text_hex`: label color, for example `#C8CDDC`.
- `style.value_text_hex`: value color, for example `#EFF3F8`.
- `style.muted_text_hex`: muted text color (section titles, stick labels), for example `#AAB2C2`.

Supported telemetry field keys:

- `height`
- `speed`
- `distance_to_home`
- `battery`
- `satellites`
- `lat`
- `lng`
- `flight_mode`
- `altitude`
- `battery_voltage`
- `battery_temp`

## AirData CSV Conversion

Some external software only accepts telemetry in AirData CSV format.

If your CSV exports are from OpenDroneLog, convert them first using one of these options:

- Web converter: https://open-dronelog.streamlit.app/
- Local script: `opendronelog_overlay/ODL_2_AD.py`

Example local conversion:

```bash
python ./opendronelog_overlay/ODL_2_AD.py ./input_odl.csv ./output_airdata.csv
```

Then use `./output_airdata.csv` with software that requires AirData-style columns.


## Love this project?

Maintaining and improving this project takes a significant amount of my free time. Your support helps keep me motivated to add new features and work on similar projects that benefit the community.

If you find this project helpful, please consider:

⭐ Starring this repository to show your support and spread the news!

☕ Buying me a coffee if you'd like to contribute to its maintenance and future development.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/arpandesign)


## Notes

- The tool assumes `time_s` in CSV starts near 0 and tracks video timeline.
- Output writes transparent `.mov` clips with alpha using `png` (default) or `qtrle` codec.
- `--output-srt` writes subtitle cues at 1 second intervals and merges unchanged consecutive lines.
