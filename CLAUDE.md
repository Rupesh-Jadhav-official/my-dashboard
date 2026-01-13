# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Windows-based terminal UI system monitoring dashboard written in Python. It displays real-time system metrics (CPU, RAM, disk, network, processes, Docker containers) using the Rich library for terminal rendering.

## Commands

```bash
# Run the dashboard
python main.py

# Run tests
python -m pytest test_main.py -v

# Run tests with HTML report (saved to reports folder with timestamp)
python -m pytest test_main.py -v --html=reports/report_YYYY-MM-DD_HH-MM-SS.html --self-contained-html
```

Windows batch files are also available: `My Dashboard.bat` (launcher) and `Run Tests.bat` (test runner with timestamped reports).

## Architecture

The application follows a functional, panel-based architecture in a single file (`main.py`):

**Data Collection Functions:**
- `get_ip_address()`, `get_cpu_temperature()`, `get_battery_status()` - System sensor data
- Uses `psutil` for system metrics, `platform`/`socket` for system info

**Panel Rendering Functions:**
- Each `make_*()` function returns a Rich `Panel` object
- `make_header()`, `make_footer()` - Chrome panels
- `make_system_info()`, `make_cpu_ram_stats()`, `make_disk_stats()`, `make_network_stats()`, `make_top_processes()`, `make_docker_stats()` - Content panels
- `make_layout()` - Assembles all panels into a grid layout

**Main Loop:**
- `main()` runs a Live refresh loop (2-second cycle)
- Non-blocking keyboard input via `msvcrt` (Windows-specific)
- Global `sort_by_memory` boolean toggles process sorting ('m' key)

**Color Coding:**
- Red: >80% usage (critical)
- Yellow: 50-80% usage (warning)
- Green: <50% usage (normal)

## Key Patterns

- Stateless panel generators that return Rich objects
- Graceful fallbacks when Docker/sensors unavailable
- All panels handle their own error cases internally
