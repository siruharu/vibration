"""Unit tests for Trend service."""
import pytest
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

from vibration.core.services.trend_service import TrendService
from vibration.core.domain.models import TrendResult


def create_synthetic_test_file(
    filepath: Path,
    sampling_rate: float = 10240.0,
    frequency: float = 100.0,
    amplitude: float = 1.0,
    duration: float = 0.5,
    channel: str = "CH1"
) -> str:
    """
    Create a synthetic vibration data file for testing.
    
    Args:
        filepath: Path to create file at.
        sampling_rate: Sampling rate in Hz.
        frequency: Sine wave frequency.
        amplitude: Signal amplitude.
        duration: Signal duration in seconds.
        channel: Channel identifier.
    
    Returns:
        File path as string.
    """
    num_samples = int(sampling_rate * duration)
    t = np.arange(num_samples) / sampling_rate
    signal = amplitude * np.sin(2 * np.pi * frequency * t)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"#Title: Test Signal\n")
        f.write(f"#D.Sampling Freq.: {sampling_rate} Hz\n")
        f.write(f"#b.Sensitivity: 100.0 mV/g\n")
        f.write(f"#Sensitivity: 100.0 mV/g\n")
        f.write(f"#Starting Time: 2026-02-06 10:00:00\n")
        f.write(f"#Record Length: {duration} sec\n")
        f.write(f"#Channel: {channel}\n")
        f.write(f"#Data Points: {num_samples}\n")
        f.write(f"#\n")
        for val in signal:
            f.write(f"{val:.8f}\n")
    
    return str(filepath)


def create_timestamped_filename(
    directory: Path,
    year: int = 2026,
    month: int = 2,
    day: int = 6,
    hour: int = 10,
    minute: int = 0,
    second: int = 0,
    channel: str = "CH1"
) -> Path:
    """Create a filename with embedded timestamp for testing."""
    timestamp = f"{year:04d}{month:02d}{day:02d}_{hour:02d}{minute:02d}{second:02d}"
    return directory / f"test_{timestamp}_{channel}.txt"


class TestTrendServiceInit:
    """Tests for TrendService initialization."""
    
    def test_init_with_default_workers(self):
        """Test service creation with default max_workers."""
        svc = TrendService()
        assert svc.max_workers is None or svc.max_workers >= 1
    
    def test_init_with_custom_workers(self):
        """Test service creation with custom max_workers."""
        svc = TrendService(max_workers=2)
        assert svc.max_workers == 2
    
    def test_get_parameters(self):
        """Test get_parameters returns correct values."""
        svc = TrendService(max_workers=4)
        params = svc.get_parameters()
        
        assert 'max_workers' in params
        assert params['max_workers'] == 4


@pytest.fixture
def trend_service():
    """Create TrendService instance with 2 workers."""
    return TrendService(max_workers=2)


@pytest.fixture
def single_test_file(tmp_path):
    """Create a single synthetic test file."""
    filepath = create_timestamped_filename(tmp_path, channel="CH1")
    create_synthetic_test_file(filepath, frequency=100.0, amplitude=1.0)
    return str(filepath)


@pytest.fixture
def multiple_test_files(tmp_path):
    """Create multiple synthetic test files with different timestamps."""
    files = []
    for i in range(3):
        filepath = create_timestamped_filename(
            tmp_path,
            hour=10 + i,
            channel=f"CH{i+1}"
        )
        create_synthetic_test_file(
            filepath,
            frequency=100.0 * (i + 1),
            amplitude=1.0 + 0.5 * i
        )
        files.append(str(filepath))
    return files


@pytest.fixture
def multi_channel_files(tmp_path):
    """Create files with same timestamp but different channels."""
    files = []
    for ch in ["CH1", "CH2", "CH3"]:
        filepath = create_timestamped_filename(tmp_path, channel=ch)
        create_synthetic_test_file(filepath, frequency=100.0, channel=ch)
        files.append(str(filepath))
    return files


class TestComputeTrend:
    """Tests for compute_trend method."""
    
    def test_returns_trend_result(self, trend_service, single_test_file):
        """Test that compute_trend returns TrendResult dataclass."""
        result = trend_service.compute_trend([single_test_file])
        
        assert isinstance(result, TrendResult)
        assert hasattr(result, 'timestamps')
        assert hasattr(result, 'rms_values')
        assert hasattr(result, 'filenames')
        assert hasattr(result, 'view_type')
    
    def test_rms_values_array_properties(self, trend_service, single_test_file):
        """Test RMS values array is non-empty and non-negative."""
        result = trend_service.compute_trend([single_test_file])
        
        assert isinstance(result.rms_values, np.ndarray)
        assert len(result.rms_values) == 1
        assert np.all(result.rms_values >= 0)
    
    def test_filenames_populated(self, trend_service, single_test_file):
        """Test that filenames are populated in result."""
        result = trend_service.compute_trend([single_test_file])
        
        assert len(result.filenames) == 1
        assert Path(single_test_file).name in result.filenames[0]
    
    def test_default_view_type_is_acc(self, trend_service, single_test_file):
        """Test default view type is ACC."""
        result = trend_service.compute_trend([single_test_file])
        assert result.view_type == 'ACC'


class TestBatchProcessing:
    """Tests for batch processing multiple files."""
    
    def test_processes_multiple_files(self, trend_service, multiple_test_files):
        """Test processing multiple files returns correct count."""
        result = trend_service.compute_trend(multiple_test_files)
        
        assert result.num_files == 3
        assert len(result.rms_values) == 3
        assert len(result.filenames) == 3
    
    def test_rms_values_differ_for_different_amplitudes(
        self, trend_service, multiple_test_files
    ):
        """Test that different amplitude signals produce different RMS values."""
        result = trend_service.compute_trend(multiple_test_files)
        unique_rms = len(set(np.round(result.rms_values, 6)))
        assert unique_rms > 1
    
    def test_progress_callback_called(self, trend_service, multiple_test_files):
        """Test that progress callback is called during processing."""
        progress_calls = []
        
        def callback(current, total):
            progress_calls.append((current, total))
        
        trend_service.compute_trend(
            multiple_test_files,
            progress_callback=callback
        )
        
        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)


class TestResultAggregation:
    """Tests for result aggregation."""
    
    def test_channel_data_populated(self, trend_service, multi_channel_files):
        """Test that channel_data is populated for multi-channel files."""
        result = trend_service.compute_trend(multi_channel_files)
        
        assert result.channel_data is not None
        assert len(result.channel_data) >= 1
    
    def test_channel_data_has_required_keys(self, trend_service, multi_channel_files):
        """Test channel_data entries have x, y, labels keys."""
        result = trend_service.compute_trend(multi_channel_files)
        
        for channel, data in result.channel_data.items():
            assert 'x' in data
            assert 'y' in data
            assert 'labels' in data
    
    def test_timestamps_extracted(self, trend_service, multiple_test_files):
        """Test timestamps are extracted from filenames."""
        result = trend_service.compute_trend(multiple_test_files)
        
        assert len(result.timestamps) == 3
        for ts in result.timestamps:
            assert isinstance(ts, datetime)
    
    def test_peak_values_populated(self, trend_service, single_test_file):
        """Test peak values are included in result."""
        result = trend_service.compute_trend([single_test_file])
        
        assert result.peak_values is not None
        assert len(result.peak_values) == 1
    
    def test_peak_frequencies_populated(self, trend_service, single_test_file):
        """Test peak frequencies are included in result."""
        result = trend_service.compute_trend([single_test_file])
        
        assert result.peak_frequencies is not None
        assert len(result.peak_frequencies) == 1
    
    def test_metadata_contains_counts(self, trend_service, multiple_test_files):
        """Test metadata contains file processing counts."""
        result = trend_service.compute_trend(multiple_test_files)
        
        assert result.metadata is not None
        assert 'total_files' in result.metadata
        assert 'success_count' in result.metadata
        assert result.metadata['total_files'] == 3


class TestViewTypes:
    """Tests for different view types (ACC, VEL, DIS)."""
    
    @pytest.fixture
    def signal_file(self, tmp_path):
        """Create a test signal file."""
        filepath = create_timestamped_filename(tmp_path)
        create_synthetic_test_file(filepath, frequency=100.0, amplitude=1.0)
        return str(filepath)
    
    def test_view_type_acc(self, trend_service, signal_file):
        """Test ACC view type."""
        result = trend_service.compute_trend([signal_file], view_type='ACC')
        assert result.view_type == 'ACC'
    
    def test_view_type_vel(self, trend_service, signal_file):
        """Test VEL view type."""
        result = trend_service.compute_trend([signal_file], view_type='VEL')
        assert result.view_type == 'VEL'
    
    def test_view_type_dis(self, trend_service, signal_file):
        """Test DIS view type."""
        result = trend_service.compute_trend([signal_file], view_type='DIS')
        assert result.view_type == 'DIS'
    
    def test_different_view_types_produce_different_rms(
        self, trend_service, signal_file
    ):
        """Test that different view types produce different RMS values."""
        result_acc = trend_service.compute_trend([signal_file], view_type='ACC')
        result_vel = trend_service.compute_trend([signal_file], view_type='VEL')
        
        assert result_acc.rms_values[0] != result_vel.rms_values[0]


class TestFrequencyBand:
    """Tests for frequency band filtering."""
    
    @pytest.fixture
    def wideband_file(self, tmp_path):
        """Create a file with wideband signal."""
        filepath = create_timestamped_filename(tmp_path)
        create_synthetic_test_file(filepath, frequency=500.0, amplitude=1.0)
        return str(filepath)
    
    def test_frequency_band_stored_in_result(self, trend_service, wideband_file):
        """Test frequency band is stored in result."""
        result = trend_service.compute_trend(
            [wideband_file],
            frequency_band=(100.0, 1000.0)
        )
        
        assert result.frequency_band == (100.0, 1000.0)
    
    def test_different_bands_produce_different_rms(
        self, trend_service, wideband_file
    ):
        """Test different frequency bands produce different RMS values."""
        result_wide = trend_service.compute_trend(
            [wideband_file],
            frequency_band=(0.0, 5000.0)
        )
        result_narrow = trend_service.compute_trend(
            [wideband_file],
            frequency_band=(400.0, 600.0)
        )
        assert result_wide.rms_values[0] != result_narrow.rms_values[0]


class TestWindowTypes:
    """Tests for different window types."""
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create a test signal file."""
        filepath = create_timestamped_filename(tmp_path)
        create_synthetic_test_file(filepath, frequency=100.0)
        return str(filepath)
    
    def test_hanning_window(self, trend_service, test_file):
        """Test processing with Hanning window."""
        result = trend_service.compute_trend(
            [test_file],
            window_type='hanning'
        )
        assert result.num_files == 1
    
    def test_flattop_window(self, trend_service, test_file):
        """Test processing with Flattop window."""
        result = trend_service.compute_trend(
            [test_file],
            window_type='flattop'
        )
        assert result.num_files == 1
    
    def test_rectangular_window(self, trend_service, test_file):
        """Test processing with Rectangular window."""
        result = trend_service.compute_trend(
            [test_file],
            window_type='rectangular'
        )
        assert result.num_files == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_file_list_returns_empty_result(self, trend_service):
        """Test empty file list returns empty TrendResult."""
        result = trend_service.compute_trend([])
        
        assert isinstance(result, TrendResult)
        assert result.num_files == 0
        assert len(result.rms_values) == 0
        assert len(result.filenames) == 0
    
    def test_nonexistent_file_handled(self, trend_service):
        """Test nonexistent file is handled gracefully."""
        result = trend_service.compute_trend(['/nonexistent/file.txt'])
        
        assert result.metadata['failed_count'] == 1
    
    def test_empty_file_handled(self, trend_service, tmp_path):
        """Test empty file is handled gracefully."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        
        result = trend_service.compute_trend([str(empty_file)])
        assert result is not None


class TestResultProperties:
    """Tests for TrendResult computed properties."""
    
    @pytest.fixture
    def result(self, trend_service, multiple_test_files):
        """Get trend result for property testing."""
        return trend_service.compute_trend(multiple_test_files)
    
    def test_num_files_property(self, result):
        """Test num_files equals filenames length."""
        assert result.num_files == len(result.filenames)
    
    def test_mean_rms_property(self, result):
        """Test mean_rms is calculated correctly."""
        expected = float(np.mean(result.rms_values))
        assert abs(result.mean_rms - expected) < 1e-10
    
    def test_max_rms_property(self, result):
        """Test max_rms is calculated correctly."""
        expected = float(np.max(result.rms_values))
        assert result.max_rms == expected
    
    def test_min_rms_property(self, result):
        """Test min_rms is calculated correctly."""
        expected = float(np.min(result.rms_values))
        assert result.min_rms == expected
    
    def test_std_rms_property(self, result):
        """Test std_rms is calculated correctly."""
        expected = float(np.std(result.rms_values))
        assert abs(result.std_rms - expected) < 1e-10


class TestNoQtDependency:
    """Verify TrendService doesn't import Qt."""
    
    def test_trend_service_no_qt_import(self):
        """Verify TrendService can be imported without loading Qt (subprocess check)."""
        import subprocess
        result = subprocess.run(
            [sys.executable, '-c', '''
import sys
from vibration.core.services.trend_service import TrendService
qt_modules = [m for m in sys.modules if 'PyQt5' in m]
if qt_modules:
    print(f"Qt modules found: {qt_modules}")
    sys.exit(1)
sys.exit(0)
'''],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"TrendService imported Qt: {result.stdout}{result.stderr}"
