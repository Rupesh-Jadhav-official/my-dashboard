from datetime import datetime
import msvcrt
import subprocess
import time
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text
import psutil

# Global state for sort mode
sort_by_memory = False


def make_header() -> Panel:
    """Create a header panel with system uptime."""
    # Calculate uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    else:
        uptime_str = f"{hours}h {minutes}m"

    header_text = Text()
    header_text.append("My Command Center", style="bold magenta")
    header_text.append("  |  ", style="dim")
    header_text.append("Uptime: ", style="dim")
    header_text.append(uptime_str, style="bold cyan")

    return Panel(header_text, style="bright_blue")


def make_footer() -> Panel:
    """Create a footer panel with current time."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sort_mode = "Memory" if sort_by_memory else "CPU"
    footer_text = Text()
    footer_text.append(f"Current Time: {current_time}", style="bold green")
    footer_text.append("  |  ", style="dim")
    footer_text.append("m", style="bold yellow")
    footer_text.append(f" sort by Memory/CPU (current: {sort_mode})", style="dim")
    footer_text.append("  |  ", style="dim")
    footer_text.append("q", style="bold yellow")
    footer_text.append(" quit", style="dim")
    return Panel(footer_text, style="bright_blue")


def make_progress_bar(percent: float, color: str, width: int = 20) -> ProgressBar:
    """Create a progress bar with the given percentage and color."""
    return ProgressBar(total=100, completed=percent, width=width, complete_style=color, finished_style=color)


def get_cpu_temperature():
    """Get CPU temperature if available."""
    try:
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if temps:
                # Try common sensor names
                for name in ['coretemp', 'cpu_thermal', 'k10temp', 'zenpower', 'acpitz']:
                    if name in temps:
                        return temps[name][0].current
                # If none found, try the first available sensor
                first_sensor = list(temps.values())[0]
                if first_sensor:
                    return first_sensor[0].current
    except Exception:
        pass
    return None


def get_battery_status():
    """Get battery status if available."""
    try:
        battery = psutil.sensors_battery()
        if battery:
            return battery
    except Exception:
        pass
    return None


def make_cpu_ram_stats() -> Panel:
    """Create a panel with CPU and RAM usage."""
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    ram_percent = memory.percent

    # Determine CPU color based on usage
    cpu_color = "red" if cpu_percent > 80 else "green"
    ram_color = "red" if ram_percent > 80 else "cyan"

    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(justify="right", width=12)
    table.add_column(justify="left", width=25)
    table.add_column(justify="right", width=8)

    cpu_bar = make_progress_bar(cpu_percent, cpu_color)
    ram_bar = make_progress_bar(ram_percent, ram_color)

    cpu_text = Text(f"{cpu_percent:5.1f}%", style=f"bold {cpu_color}")
    ram_text = Text(f"{ram_percent:5.1f}%", style=f"bold {ram_color}")

    table.add_row("CPU Usage:", cpu_bar, cpu_text)

    # Add CPU temperature if available
    cpu_temp = get_cpu_temperature()
    if cpu_temp is not None:
        temp_color = "red" if cpu_temp > 80 else "yellow" if cpu_temp > 60 else "green"
        table.add_row("CPU Temp:", Text(f"{cpu_temp:.1f}°C", style=f"bold {temp_color}"))
    else:
        table.add_row("CPU Temp:", Text("N/A", style="dim"))

    table.add_row("RAM Usage:", ram_bar, ram_text)
    table.add_row("RAM Used:", Text(f"{memory.used / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB", style="dim"))

    # Add battery status if available
    battery = get_battery_status()
    if battery:
        bat_percent = battery.percent
        bat_color = "red" if bat_percent < 20 else "yellow" if bat_percent < 50 else "green"
        bat_bar = make_progress_bar(bat_percent, bat_color)
        bat_text = Text(f"{bat_percent:5.1f}%", style=f"bold {bat_color}")

        # Status indicator
        if battery.power_plugged:
            status = Text(" [Charging]", style="bold green") if bat_percent < 100 else Text(" [Full]", style="bold green")
        else:
            # Calculate time remaining
            if battery.secsleft > 0 and battery.secsleft != psutil.POWER_TIME_UNLIMITED:
                hours, remainder = divmod(battery.secsleft, 3600)
                minutes, _ = divmod(remainder, 60)
                status = Text(f" [{int(hours)}h {int(minutes)}m left]", style="dim")
            else:
                status = Text(" [Discharging]", style="yellow")

        table.add_row("Battery:", bat_bar, bat_text)
        table.add_row("", status)

    return Panel(table, title="CPU & Memory", border_style="bright_blue")


def make_disk_stats() -> Panel:
    """Create a panel with disk usage."""
    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(justify="right", width=12)
    table.add_column(justify="left", width=25)
    table.add_column(justify="right", width=8)

    # Get all disk partitions
    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_percent = usage.percent
            disk_color = "red" if disk_percent > 90 else "yellow" if disk_percent > 70 else "green"

            disk_bar = make_progress_bar(disk_percent, disk_color)
            disk_text = Text(f"{disk_percent:5.1f}%", style=f"bold {disk_color}")

            free_gb = usage.free / (1024**3)
            free_color = "red" if free_gb < 10 else "yellow" if free_gb < 50 else "green"

            table.add_row(f"{partition.device}:", disk_bar, disk_text)
            table.add_row("  Used:", Text(f"{usage.used / (1024**3):.1f} GB / {usage.total / (1024**3):.1f} GB", style="dim"))
            table.add_row("  Free:", Text(f"{free_gb:.1f} GB", style=f"bold {free_color}"))
        except (PermissionError, OSError):
            continue

    return Panel(table, title="Disk Usage", border_style="bright_blue")


def make_network_stats() -> Panel:
    """Create a panel with network statistics."""
    net_io = psutil.net_io_counters()

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right")
    table.add_column(justify="left")

    bytes_sent = net_io.bytes_sent
    bytes_recv = net_io.bytes_recv

    # Format bytes to appropriate unit
    def format_bytes(b):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024:
                return f"{b:.2f} {unit}"
            b /= 1024
        return f"{b:.2f} PB"

    sent_text = Text(format_bytes(bytes_sent), style="bold yellow")
    recv_text = Text(format_bytes(bytes_recv), style="bold cyan")

    table.add_row("Bytes Sent:", sent_text)
    table.add_row("Bytes Received:", recv_text)
    table.add_row("Packets Sent:", f"{net_io.packets_sent:,}")
    table.add_row("Packets Received:", f"{net_io.packets_recv:,}")

    return Panel(table, title="Network Stats", border_style="bright_blue")


def make_top_processes() -> Panel:
    """Create a panel showing top 5 processes by CPU or memory usage."""
    sort_key = 'memory_percent' if sort_by_memory else 'cpu_percent'
    sort_label = "Memory" if sort_by_memory else "CPU"

    table = Table(expand=True, box=None, padding=(0, 1))
    table.add_column("PID", justify="right", style="cyan", width=7)
    table.add_column("Name", justify="left", style="white", no_wrap=True)
    table.add_column("CPU %", justify="right", width=7)
    table.add_column("Mem %", justify="right", width=7)

    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] is not None:
                processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort by selected metric descending and get top 5
    top_processes = sorted(processes, key=lambda x: x[sort_key] or 0, reverse=True)[:5]

    for proc in top_processes:
        cpu = proc['cpu_percent'] or 0
        mem = proc['memory_percent'] or 0
        cpu_color = "red" if cpu > 50 else "yellow" if cpu > 20 else "green"
        mem_color = "red" if mem > 50 else "yellow" if mem > 20 else "cyan"

        table.add_row(
            str(proc['pid']),
            proc['name'][:20] if proc['name'] else "N/A",
            Text(f"{cpu:.1f}%", style=f"bold {cpu_color}"),
            Text(f"{mem:.1f}%", style=f"bold {mem_color}")
        )

    return Panel(table, title=f"Top Processes (by {sort_label})", border_style="bright_blue")


def make_docker_stats() -> Panel:
    """Create a panel showing Docker container stats."""
    table = Table(expand=True, box=None, padding=(0, 1))
    table.add_column("Container", justify="left", style="cyan", no_wrap=True)
    table.add_column("Image", justify="left", style="dim", no_wrap=True)
    table.add_column("Status", justify="left", width=12)
    table.add_column("CPU %", justify="right", width=8)
    table.add_column("Mem Usage", justify="right", width=18)

    try:
        # Get running containers
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}\t{{.Image}}\t{{.Status}}'],
            capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW
        )

        if result.returncode != 0:
            return Panel(Text("Docker not available or not running", style="dim"), title="Docker Containers", border_style="bright_blue")

        containers = result.stdout.strip().split('\n')
        if not containers or containers == ['']:
            return Panel(Text("No running containers", style="dim"), title="Docker Containers", border_style="bright_blue")

        # Get stats for running containers
        stats_result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'],
            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW
        )

        stats_dict = {}
        if stats_result.returncode == 0:
            for line in stats_result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        stats_dict[parts[0]] = {'cpu': parts[1], 'mem': parts[2]}

        for container in containers:
            if not container:
                continue
            parts = container.split('\t')
            if len(parts) >= 3:
                name = parts[0][:15]
                image = parts[1][:20]
                status = parts[2].split()[0] if parts[2] else "Unknown"

                # Color status
                status_color = "green" if "Up" in parts[2] else "red"
                status_text = Text(status, style=f"bold {status_color}")

                # Get stats
                stats = stats_dict.get(parts[0], {})
                cpu = stats.get('cpu', 'N/A')
                mem = stats.get('mem', 'N/A')

                # Color CPU
                cpu_val = float(cpu.replace('%', '')) if cpu != 'N/A' and '%' in cpu else 0
                cpu_color = "red" if cpu_val > 80 else "yellow" if cpu_val > 50 else "green"
                cpu_text = Text(cpu, style=f"bold {cpu_color}") if cpu != 'N/A' else Text("N/A", style="dim")

                table.add_row(name, image, status_text, cpu_text, mem)

    except FileNotFoundError:
        return Panel(Text("Docker is not installed", style="dim"), title="Docker Containers", border_style="bright_blue")
    except subprocess.TimeoutExpired:
        return Panel(Text("Docker command timed out", style="dim"), title="Docker Containers", border_style="bright_blue")
    except Exception as e:
        return Panel(Text(f"Error: {str(e)[:30]}", style="red"), title="Docker Containers", border_style="bright_blue")

    return Panel(table, title="Docker Containers", border_style="bright_blue")


def make_layout() -> Layout:
    """Create and populate the layout."""
    layout = Layout()

    # Split into header, body, docker, and footer
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="docker", size=10),
        Layout(name="footer", size=3),
    )

    # Split body into left and right columns
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    # Split left column into CPU/RAM and Disk
    layout["left"].split_column(
        Layout(name="cpu_ram"),
        Layout(name="disk"),
    )

    # Split right column for network stats and top processes
    layout["right"].split_column(
        Layout(name="network"),
        Layout(name="processes"),
    )

    # Assign content to each section
    layout["header"].update(make_header())
    layout["cpu_ram"].update(make_cpu_ram_stats())
    layout["disk"].update(make_disk_stats())
    layout["network"].update(make_network_stats())
    layout["processes"].update(make_top_processes())
    layout["docker"].update(make_docker_stats())
    layout["footer"].update(make_footer())

    return layout


def main():
    global sort_by_memory
    console = Console()

    # Initial CPU reading to avoid 0% on first call
    psutil.cpu_percent(interval=None)

    # Use Live to auto-refresh every 2 seconds
    with Live(make_layout(), console=console, refresh_per_second=0.5, screen=True) as live:
        while True:
            # Check for keyboard input
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                if key == 'q':
                    break
                elif key == 'm':
                    sort_by_memory = not sort_by_memory
            live.update(make_layout())
            time.sleep(0.1)  # Small delay to reduce CPU usage


if __name__ == "__main__":
    main()
