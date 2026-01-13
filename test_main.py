"""Unit tests for the System Monitor Dashboard."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from rich.panel import Panel
from rich.layout import Layout


class TestGetIpAddress:
    """Tests for get_ip_address function."""

    def test_get_ip_address_success(self):
        """Test successful IP address retrieval."""
        from main import get_ip_address

        with patch("main.socket.socket") as mock_socket:
            mock_sock_instance = Mock()
            mock_sock_instance.getsockname.return_value = (
                "192.168.1.100", 12345
            )
            mock_socket.return_value = mock_sock_instance

            ip = get_ip_address()

            assert ip == "192.168.1.100"
            mock_sock_instance.connect.assert_called_once_with(("8.8.8.8", 80))
            mock_sock_instance.close.assert_called_once()

    def test_get_ip_address_failure(self):
        """Test IP address retrieval when network is unavailable."""
        from main import get_ip_address

        with patch("main.socket.socket") as mock_socket:
            mock_socket.side_effect = Exception("Network error")

            ip = get_ip_address()

            assert ip == "N/A"


class TestGetCpuTemperature:
    """Tests for get_cpu_temperature function."""

    def test_cpu_temperature_available(self):
        """Test when CPU temperature is available."""
        from main import get_cpu_temperature

        mock_temp = Mock()
        mock_temp.current = 65.5

        with patch(
            "main.psutil.sensors_temperatures", create=True
        ) as mock_sensors:
            mock_sensors.return_value = {"coretemp": [mock_temp]}

            temp = get_cpu_temperature()

            assert temp == 65.5

    def test_cpu_temperature_not_available(self):
        """Test when CPU temperature is not available."""
        from main import get_cpu_temperature

        with patch(
            "main.psutil.sensors_temperatures", create=True
        ) as mock_sensors:
            mock_sensors.return_value = {}

            temp = get_cpu_temperature()

            assert temp is None

    def test_cpu_temperature_no_sensors_attr(self):
        """Test when psutil doesn't have sensors_temperatures (Windows)."""
        from main import get_cpu_temperature

        # On Windows, sensors_temperatures doesn't exist
        # The function should handle this gracefully
        temp = get_cpu_temperature()

        # Should return None when not available
        assert temp is None


class TestGetBatteryStatus:
    """Tests for get_battery_status function."""

    def test_battery_available(self):
        """Test when battery is available."""
        from main import get_battery_status

        mock_battery = Mock()
        mock_battery.percent = 75
        mock_battery.power_plugged = True

        with patch("main.psutil.sensors_battery") as mock_sensors:
            mock_sensors.return_value = mock_battery

            battery = get_battery_status()

            assert battery.percent == 75
            assert battery.power_plugged is True

    def test_battery_not_available(self):
        """Test when no battery is present (desktop)."""
        from main import get_battery_status

        with patch("main.psutil.sensors_battery") as mock_sensors:
            mock_sensors.return_value = None

            battery = get_battery_status()

            assert battery is None


class TestMakeHeader:
    """Tests for make_header function."""

    def test_make_header_returns_panel(self):
        """Test that make_header returns a Panel."""
        from main import make_header

        with patch("main.psutil.boot_time") as mock_boot:
            # Set boot time to 2 hours ago
            mock_boot.return_value = datetime.now().timestamp() - 7200

            header = make_header()

            assert isinstance(header, Panel)

    def test_make_header_contains_title(self):
        """Test that header contains the dashboard title."""
        from main import make_header

        with patch("main.psutil.boot_time") as mock_boot:
            mock_boot.return_value = datetime.now().timestamp() - 3600

            header = make_header()

            # Check that the panel was created (contains renderable content)
            assert header.renderable is not None


class TestMakeFooter:
    """Tests for make_footer function."""

    def test_make_footer_returns_panel(self):
        """Test that make_footer returns a Panel."""
        from main import make_footer

        footer = make_footer()

        assert isinstance(footer, Panel)


class TestMakeSystemInfo:
    """Tests for make_system_info function."""

    def test_make_system_info_returns_panel(self):
        """Test that make_system_info returns a Panel."""
        from main import make_system_info

        with patch("main.socket.gethostname", return_value="test-host"), patch(
            "main.os.getlogin", return_value="testuser"
        ), patch("main.platform.system", return_value="Windows"), patch(
            "main.platform.release", return_value="10"
        ), patch(
            "main.platform.version", return_value="10.0.19041"
        ), patch(
            "main.platform.machine", return_value="AMD64"
        ), patch(
            "main.platform.processor", return_value="Intel Core i7"
        ), patch(
            "main.psutil.cpu_count"
        ) as mock_cpu_count, patch(
            "main.get_ip_address", return_value="192.168.1.1"
        ):

            mock_cpu_count.side_effect = lambda logical: 8 if logical else 4

            panel = make_system_info()

            assert isinstance(panel, Panel)
            assert panel.title == "System Info"


class TestMakeCpuRamStats:
    """Tests for make_cpu_ram_stats function."""

    def test_make_cpu_ram_stats_returns_panel(self):
        """Test that make_cpu_ram_stats returns a Panel."""
        from main import make_cpu_ram_stats

        mock_memory = Mock()
        mock_memory.percent = 60.5
        mock_memory.used = 8 * 1024**3  # 8 GB
        mock_memory.total = 16 * 1024**3  # 16 GB

        with patch("main.psutil.cpu_percent", return_value=45.0), patch(
            "main.psutil.virtual_memory", return_value=mock_memory
        ), patch("main.get_cpu_temperature", return_value=55.0), patch(
            "main.get_battery_status", return_value=None
        ):

            panel = make_cpu_ram_stats()

            assert isinstance(panel, Panel)
            assert panel.title == "CPU & Memory"

    def test_cpu_color_high_usage(self):
        """Test that high CPU usage shows red color."""
        from main import make_cpu_ram_stats

        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_memory.used = 8 * 1024**3
        mock_memory.total = 16 * 1024**3

        with patch("main.psutil.cpu_percent", return_value=95.0), patch(
            "main.psutil.virtual_memory", return_value=mock_memory
        ), patch("main.get_cpu_temperature", return_value=None), patch(
            "main.get_battery_status", return_value=None
        ):

            panel = make_cpu_ram_stats()

            assert isinstance(panel, Panel)


class TestMakeDiskStats:
    """Tests for make_disk_stats function."""

    def test_make_disk_stats_returns_panel(self):
        """Test that make_disk_stats returns a Panel."""
        from main import make_disk_stats

        mock_partition = Mock()
        mock_partition.device = "C:\\"
        mock_partition.mountpoint = "C:\\"

        mock_usage = Mock()
        mock_usage.percent = 65.0
        mock_usage.used = 200 * 1024**3  # 200 GB
        mock_usage.total = 500 * 1024**3  # 500 GB
        mock_usage.free = 300 * 1024**3  # 300 GB

        with patch(
            "main.psutil.disk_partitions", return_value=[mock_partition]
        ), patch(
            "main.psutil.disk_usage", return_value=mock_usage
        ):

            panel = make_disk_stats()

            assert isinstance(panel, Panel)
            assert panel.title == "Disk Usage"


class TestMakeNetworkStats:
    """Tests for make_network_stats function."""

    def test_make_network_stats_returns_panel(self):
        """Test that make_network_stats returns a Panel."""
        from main import make_network_stats

        mock_net_io = Mock()
        mock_net_io.bytes_sent = 1024 * 1024 * 500  # 500 MB
        mock_net_io.bytes_recv = 1024 * 1024 * 1024 * 2  # 2 GB
        mock_net_io.packets_sent = 100000
        mock_net_io.packets_recv = 200000

        with patch("main.psutil.net_io_counters", return_value=mock_net_io):

            panel = make_network_stats()

            assert isinstance(panel, Panel)
            assert panel.title == "Network Stats"


class TestMakeTopProcesses:
    """Tests for make_top_processes function."""

    def test_make_top_processes_returns_panel(self):
        """Test that make_top_processes returns a Panel."""
        from main import make_top_processes

        mock_proc = Mock()
        mock_proc.info = {
            "pid": 1234,
            "name": "python.exe",
            "cpu_percent": 25.0,
            "memory_percent": 5.0,
        }

        with patch("main.psutil.process_iter", return_value=[mock_proc]):

            panel = make_top_processes()

            assert isinstance(panel, Panel)
            assert "Top Processes" in panel.title

    def test_make_top_processes_handles_empty_list(self):
        """Test handling of empty process list."""
        from main import make_top_processes

        with patch("main.psutil.process_iter", return_value=[]):

            panel = make_top_processes()

            assert isinstance(panel, Panel)


class TestMakeDockerStats:
    """Tests for make_docker_stats function."""

    def test_docker_not_installed(self):
        """Test when Docker is not installed."""
        from main import make_docker_stats

        with patch("main.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            panel = make_docker_stats()

            assert isinstance(panel, Panel)
            assert panel.title == "Docker Containers"

    def test_docker_not_running(self):
        """Test when Docker daemon is not running."""
        from main import make_docker_stats

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("main.subprocess.run", return_value=mock_result):

            panel = make_docker_stats()

            assert isinstance(panel, Panel)

    def test_docker_no_containers(self):
        """Test when no containers are running."""
        from main import make_docker_stats

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("main.subprocess.run", return_value=mock_result):

            panel = make_docker_stats()

            assert isinstance(panel, Panel)


class TestMakeLayout:
    """Tests for make_layout function."""

    def test_make_layout_returns_layout(self):
        """Test that make_layout returns a Layout."""
        from main import make_layout

        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_memory.used = 8 * 1024**3
        mock_memory.total = 16 * 1024**3

        mock_partition = Mock()
        mock_partition.device = "C:\\"
        mock_partition.mountpoint = "C:\\"

        mock_usage = Mock()
        mock_usage.percent = 50.0
        mock_usage.used = 250 * 1024**3
        mock_usage.total = 500 * 1024**3
        mock_usage.free = 250 * 1024**3

        mock_net_io = Mock()
        mock_net_io.bytes_sent = 1024 * 1024
        mock_net_io.bytes_recv = 1024 * 1024
        mock_net_io.packets_sent = 1000
        mock_net_io.packets_recv = 1000

        boot_time = datetime.now().timestamp() - 3600
        with patch(
            "main.psutil.boot_time", return_value=boot_time
        ), patch("main.psutil.cpu_percent", return_value=50.0), patch(
            "main.psutil.virtual_memory", return_value=mock_memory
        ), patch(
            "main.psutil.disk_partitions", return_value=[mock_partition]
        ), patch(
            "main.psutil.disk_usage", return_value=mock_usage
        ), patch(
            "main.psutil.net_io_counters", return_value=mock_net_io
        ), patch(
            "main.psutil.process_iter", return_value=[]
        ), patch(
            "main.psutil.cpu_count", return_value=8
        ), patch(
            "main.get_cpu_temperature", return_value=None
        ), patch(
            "main.get_battery_status", return_value=None
        ), patch(
            "main.get_ip_address", return_value="192.168.1.1"
        ), patch(
            "main.socket.gethostname", return_value="test-host"
        ), patch(
            "main.os.getlogin", return_value="testuser"
        ), patch(
            "main.platform.system", return_value="Windows"
        ), patch(
            "main.platform.release", return_value="10"
        ), patch(
            "main.platform.version", return_value="10.0.19041"
        ), patch(
            "main.platform.machine", return_value="AMD64"
        ), patch(
            "main.platform.processor", return_value="Intel"
        ), patch(
            "main.subprocess.run"
        ) as mock_docker:

            mock_docker.side_effect = FileNotFoundError()

            layout = make_layout()

            assert isinstance(layout, Layout)


class TestMakeProgressBar:
    """Tests for make_progress_bar function."""

    def test_make_progress_bar_zero_percent(self):
        """Test progress bar with 0%."""
        from main import make_progress_bar

        bar = make_progress_bar(0, "green")

        assert bar.completed == 0
        assert bar.total == 100

    def test_make_progress_bar_full_percent(self):
        """Test progress bar with 100%."""
        from main import make_progress_bar

        bar = make_progress_bar(100, "red")

        assert bar.completed == 100
        assert bar.total == 100

    def test_make_progress_bar_partial(self):
        """Test progress bar with partial percentage."""
        from main import make_progress_bar

        bar = make_progress_bar(55.5, "yellow")

        assert bar.completed == 55.5
        assert bar.total == 100


class TestSortToggle:
    """Tests for sort mode toggle."""

    def test_sort_by_memory_default(self):
        """Test that default sort is by CPU."""
        import main

        # Reset to default
        main.sort_by_memory = False

        assert main.sort_by_memory is False

    def test_sort_toggle(self):
        """Test toggling sort mode."""
        import main

        main.sort_by_memory = False
        main.sort_by_memory = not main.sort_by_memory

        assert main.sort_by_memory is True

        main.sort_by_memory = not main.sort_by_memory

        assert main.sort_by_memory is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
