"""Unit tests for FFT service."""
import pytest
import numpy as np
import sys

from vibration.core.services.fft_service import FFTService
from vibration.core.domain.models import FFTResult


class TestFFTServiceInit:
    """Tests for FFTService initialization."""
    
    def test_init_with_default_window(self):
        """Test service creation with default window type."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0
        )
        assert svc.sampling_rate == 10240.0
        assert svc.delta_f == 1.0
        assert svc.overlap == 50.0
        assert svc.window_type == 'hanning'
    
    def test_init_with_custom_window(self):
        """Test service creation with custom window type."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='hamming'
        )
        assert svc.window_type == 'hamming'
    
    def test_get_parameters(self):
        """Test get_parameters returns correct values."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='hamming'
        )
        params = svc.get_parameters()
        
        assert params['sampling_rate'] == 10240.0
        assert params['delta_f'] == 1.0
        assert params['overlap'] == 50.0
        assert params['window_type'] == 'hamming'
        assert params['nfft'] == 10240


@pytest.fixture
def fft_service():
    """Create FFT service instance with standard parameters."""
    return FFTService(
        sampling_rate=10240.0,
        delta_f=1.0,
        overlap=50.0,
        window_type='hanning'
    )


@pytest.fixture
def sine_wave_100hz():
    """Generate 100 Hz sine wave with sufficient length (1.5s at 10240 Hz)."""
    fs = 10240.0
    duration = 1.5
    t = np.arange(0, duration, 1/fs)
    return np.sin(2 * np.pi * 100 * t)


@pytest.fixture
def multi_frequency_signal():
    """Generate signal: 100 Hz (amp=1.0) + 500 Hz (amp=0.5)."""
    fs = 10240.0
    duration = 1.5
    t = np.arange(0, duration, 1/fs)
    return np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 500 * t)


class TestComputeSpectrum:
    """Tests for compute_spectrum method."""
    
    def test_returns_fft_result(self, fft_service, sine_wave_100hz):
        """Test that compute_spectrum returns FFTResult dataclass."""
        result = fft_service.compute_spectrum(sine_wave_100hz)
        
        assert isinstance(result, FFTResult)
        assert hasattr(result, 'frequency')
        assert hasattr(result, 'spectrum')
        assert hasattr(result, 'view_type')
        assert hasattr(result, 'window_type')
    
    def test_frequency_array_properties(self, fft_service, sine_wave_100hz):
        """Test frequency array starts at 0, is monotonic, has correct resolution."""
        result = fft_service.compute_spectrum(sine_wave_100hz)
        
        assert result.frequency[0] == 0.0
        assert np.all(np.diff(result.frequency) >= 0)
        freq_resolution = result.frequency[1] - result.frequency[0]
        assert abs(freq_resolution - 1.0) < 0.01
    
    def test_spectrum_array_properties(self, fft_service, sine_wave_100hz):
        """Test spectrum has same length as frequency, non-negative, DC zeroed."""
        result = fft_service.compute_spectrum(sine_wave_100hz)
        
        assert len(result.spectrum) == len(result.frequency)
        assert np.all(result.spectrum >= 0)
        assert result.spectrum[0] == 0
    
    def test_detects_100hz_peak(self, fft_service, sine_wave_100hz):
        """Test that 100 Hz sine wave produces peak at 100 Hz."""
        result = fft_service.compute_spectrum(sine_wave_100hz)
        
        peak_idx = np.argmax(result.spectrum)
        peak_freq = result.frequency[peak_idx]
        
        assert abs(peak_freq - 100.0) < 2.0
    
    def test_detects_multiple_peaks(self, fft_service, multi_frequency_signal):
        """Test that multi-frequency signal produces peaks at correct frequencies."""
        result = fft_service.compute_spectrum(multi_frequency_signal)
        
        idx_100 = np.argmin(np.abs(result.frequency - 100))
        idx_500 = np.argmin(np.abs(result.frequency - 500))
        
        local_100 = result.spectrum[max(0, idx_100-5):idx_100+5]
        local_500 = result.spectrum[max(0, idx_500-5):idx_500+5]
        
        assert np.max(local_100) > 0
        assert np.max(local_500) > 0
        assert np.max(local_100) > np.max(local_500) * 1.5
    
    def test_result_metadata(self, fft_service, sine_wave_100hz):
        """Test that result contains correct metadata."""
        result = fft_service.compute_spectrum(sine_wave_100hz)
        
        assert result.sampling_rate == 10240.0
        assert result.delta_f == 1.0
        assert result.overlap == 50.0
        assert result.window_type == 'hanning'
        assert result.acf >= 0
        assert result.ecf >= 0


class TestWindowTypes:
    """Tests for different window types."""
    
    @pytest.fixture
    def signal_data(self):
        """Generate 100 Hz test signal."""
        fs = 10240.0
        t = np.arange(0, 1.5, 1/fs)
        return np.sin(2 * np.pi * 100 * t)
    
    def test_hanning_window(self, signal_data):
        """Test FFT with Hanning window."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='hanning'
        )
        result = svc.compute_spectrum(signal_data)
        assert result.window_type == 'hanning'
    
    @pytest.mark.xfail(reason="scipy.signal.flattop not available in this scipy version")
    def test_flattop_window(self, signal_data):
        """Test FFT with Flattop window."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='flattop'
        )
        result = svc.compute_spectrum(signal_data)
        assert result.window_type == 'flattop'
    
    def test_hamming_window(self, signal_data):
        """Test FFT with Hamming window."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='hamming'
        )
        result = svc.compute_spectrum(signal_data)
        assert result.window_type == 'hamming'
    
    def test_blackman_window(self, signal_data):
        """Test FFT with Blackman window."""
        svc = FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='blackman'
        )
        result = svc.compute_spectrum(signal_data)
        assert result.window_type == 'blackman'
    
    def test_different_windows_produce_different_spectra(self, signal_data):
        """Test that different windows produce different spectrum shapes."""
        svc_hanning = FFTService(
            sampling_rate=10240.0, delta_f=1.0, overlap=50.0, window_type='hanning'
        )
        svc_blackman = FFTService(
            sampling_rate=10240.0, delta_f=1.0, overlap=50.0, window_type='blackman'
        )
        
        result_hanning = svc_hanning.compute_spectrum(signal_data)
        result_blackman = svc_blackman.compute_spectrum(signal_data)
        
        peak_han = result_hanning.frequency[np.argmax(result_hanning.spectrum)]
        peak_blk = result_blackman.frequency[np.argmax(result_blackman.spectrum)]
        assert abs(peak_han - peak_blk) < 2.0
        
        amp_han = np.max(result_hanning.spectrum)
        amp_blk = np.max(result_blackman.spectrum)
        assert amp_han != amp_blk


class TestViewTypes:
    """Tests for different view types (ACC, VEL, DIS)."""
    
    @pytest.fixture
    def signal_data(self):
        """Generate 100 Hz test signal."""
        fs = 10240.0
        t = np.arange(0, 1.5, 1/fs)
        return np.sin(2 * np.pi * 100 * t)
    
    def test_view_type_acc(self, fft_service, signal_data):
        """Test FFT with ACC view type."""
        result = fft_service.compute_spectrum(signal_data, view_type='ACC')
        assert result.view_type == 'ACC'
    
    def test_view_type_vel(self, fft_service, signal_data):
        """Test FFT with VEL view type."""
        result = fft_service.compute_spectrum(signal_data, view_type='VEL')
        assert result.view_type == 'VEL'
    
    def test_view_type_dis(self, fft_service, signal_data):
        """Test FFT with DIS view type."""
        result = fft_service.compute_spectrum(signal_data, view_type='DIS')
        assert result.view_type == 'DIS'
    
    def test_vel_amplitude_differs_from_acc(self, fft_service, signal_data):
        """Test that VEL view produces different amplitude than ACC."""
        result_acc = fft_service.compute_spectrum(signal_data, view_type='ACC')
        result_vel = fft_service.compute_spectrum(signal_data, view_type='VEL')
        
        peak_acc = np.max(result_acc.spectrum)
        peak_vel = np.max(result_vel.spectrum)
        assert peak_acc != peak_vel
    
    def test_dis_amplitude_differs_from_acc(self, fft_service, signal_data):
        """Test that DIS view produces different amplitude than ACC."""
        result_acc = fft_service.compute_spectrum(signal_data, view_type='ACC')
        result_dis = fft_service.compute_spectrum(signal_data, view_type='DIS')
        
        peak_acc = np.max(result_acc.spectrum)
        peak_dis = np.max(result_dis.spectrum)
        assert peak_acc != peak_dis
    
    def test_all_view_types_have_same_frequency_axis(self, fft_service, signal_data):
        """Test that all view types produce same frequency axis."""
        result_acc = fft_service.compute_spectrum(signal_data, view_type='ACC')
        result_vel = fft_service.compute_spectrum(signal_data, view_type='VEL')
        result_dis = fft_service.compute_spectrum(signal_data, view_type='DIS')
        
        np.testing.assert_array_equal(result_acc.frequency, result_vel.frequency)
        np.testing.assert_array_equal(result_acc.frequency, result_dis.frequency)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_data_raises_error(self, fft_service):
        """Test that empty data raises ValueError."""
        with pytest.raises(ValueError):
            fft_service.compute_spectrum(np.array([]))
    
    def test_insufficient_data_raises_error(self, fft_service):
        """Test that data shorter than NFFT (10240) raises error."""
        short_data = np.random.randn(100)
        with pytest.raises(ValueError) as exc_info:
            fft_service.compute_spectrum(short_data)
        
        assert "shorter than required NFFT" in str(exc_info.value)
    
    def test_single_point_raises_error(self, fft_service):
        """Test that single data point raises ValueError."""
        with pytest.raises(ValueError):
            fft_service.compute_spectrum(np.array([1.0]))
    
    def test_exact_nfft_samples(self, fft_service):
        """Test FFT with exactly NFFT (10240) samples."""
        data = np.random.randn(10240)
        result = fft_service.compute_spectrum(data)
        assert isinstance(result, FFTResult)
        assert len(result.spectrum) > 0
    
    def test_handles_nan_values(self, fft_service):
        """Test behavior with NaN values in data."""
        data = np.random.randn(15360)
        data[1000] = np.nan
        
        try:
            result = fft_service.compute_spectrum(data)
            assert result is not None
        except (ValueError, RuntimeError):
            pass
    
    def test_handles_inf_values(self, fft_service):
        """Test behavior with infinite values in data."""
        data = np.random.randn(15360)
        data[1000] = np.inf
        
        try:
            result = fft_service.compute_spectrum(data)
            assert result is not None
        except (ValueError, RuntimeError):
            pass
    
    def test_handles_all_zeros(self, fft_service):
        """Test FFT of all-zero signal produces zero spectrum."""
        data = np.zeros(15360)
        result = fft_service.compute_spectrum(data)
        
        assert np.allclose(result.spectrum, 0, atol=1e-10)
    
    def test_handles_constant_signal(self, fft_service):
        """Test FFT of constant (DC) signal has zeroed DC component."""
        data = np.ones(15360) * 5.0
        result = fft_service.compute_spectrum(data)
        
        assert result.spectrum[0] == 0


class TestZeroPadding:
    """Tests for zero padding functionality."""
    
    @pytest.fixture
    def signal_data(self):
        """Generate signal with 10 Hz and 100 Hz components."""
        fs = 10240.0
        t = np.arange(0, 1.5, 1/fs)
        return np.sin(2 * np.pi * 10 * t) + np.sin(2 * np.pi * 100 * t)
    
    def test_zero_padding_removes_low_frequencies(self, fft_service, signal_data):
        """Test that zero padding removes low frequency content."""
        result_no_pad = fft_service.compute_spectrum(signal_data, zero_padding_freq=0.0)
        result_padded = fft_service.compute_spectrum(signal_data, zero_padding_freq=50.0)
        
        low_freq_mask = result_padded.frequency < 50.0
        
        assert np.allclose(result_padded.spectrum[low_freq_mask], 0)
        assert np.max(result_no_pad.spectrum[low_freq_mask]) > 0


class TestResultProperties:
    """Tests for FFTResult computed properties."""
    
    @pytest.fixture
    def result(self, fft_service, sine_wave_100hz):
        """Get FFT result for property testing."""
        return fft_service.compute_spectrum(sine_wave_100hz)
    
    def test_max_frequency_property(self, result):
        """Test max_frequency equals last frequency value."""
        assert result.max_frequency == result.frequency[-1]
        assert result.max_frequency > 0
    
    def test_peak_frequency_property(self, result):
        """Test peak_frequency is near 100 Hz for 100 Hz input."""
        assert abs(result.peak_frequency - 100.0) < 2.0
    
    def test_peak_amplitude_property(self, result):
        """Test peak_amplitude equals max spectrum value."""
        assert result.peak_amplitude == np.max(result.spectrum)
        assert result.peak_amplitude > 0
    
    def test_num_points_property(self, result):
        """Test num_points equals array lengths."""
        assert result.num_points == len(result.frequency)
        assert result.num_points == len(result.spectrum)


class TestNoQtDependency:
    """Verify FFTService doesn't import Qt."""
    
    def test_fft_service_no_qt_import(self):
        """Verify FFTService can be imported without loading Qt (subprocess check)."""
        import subprocess
        result = subprocess.run(
            [sys.executable, '-c', '''
import sys
from vibration.core.services.fft_service import FFTService
qt_modules = [m for m in sys.modules if 'PyQt5' in m]
if qt_modules:
    print(f"Qt modules found: {qt_modules}")
    sys.exit(1)
sys.exit(0)
'''],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"FFTService imported Qt: {result.stdout}{result.stderr}"
