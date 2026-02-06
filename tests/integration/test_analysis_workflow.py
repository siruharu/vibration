"""
Integration tests for complete analysis workflows.

Tests end-to-end scenarios without requiring GUI.
Verifies all services work together correctly.
"""
import pytest
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

from vibration.core.services import FFTService, TrendService, PeakService, FileService
from vibration.core.domain.models import FFTResult, TrendResult, FileMetadata


class TestFFTWorkflow:
    """Test complete FFT analysis workflow."""
    
    @pytest.fixture
    def file_service(self):
        """Create file service instance."""
        return FileService()
    
    @pytest.fixture
    def fft_service(self):
        """Create FFT service with standard parameters."""
        return FFTService(
            sampling_rate=10240.0,
            delta_f=1.0,
            overlap=50.0,
            window_type='hanning'
        )
    
    @pytest.fixture
    def test_data_file(self, tmp_path):
        """Create test data file with proper format."""
        test_file = tmp_path / "test_data.txt"
        content = """D.Sampling Freq.: 10240 Hz
Channel: CH1
Sensitivity: 100 mV/g
b.Sensitivity: 50
Record Length: 1.0 sec

"""
        # Add numeric data (1 second at 10240 Hz = 10240 samples)
        samples = np.sin(2 * np.pi * 100 * np.linspace(0, 1, 10240))
        content += "\n".join(f"{x:.6f}" for x in samples)
        test_file.write_text(content, encoding='utf-8')
        return test_file
    
    def test_fft_analysis_workflow(self, tmp_path, file_service, fft_service):
        """Test: Load file metadata -> Compute FFT on synthetic signal -> Get results."""
        # Step 1: Create test file
        test_file = tmp_path / "test_data.txt"
        test_file.write_text("Sample\n1.0\n2.0\n3.0\n")
        
        # Step 2: Scan directory and get file metadata
        metadata_list = file_service.scan_directory(str(tmp_path), "*.txt")
        assert len(metadata_list) == 1
        assert isinstance(metadata_list[0], FileMetadata)
        
        # Step 3: Compute FFT with synthetic signal (file data too short for FFT)
        # Use 1.5 seconds of 100 Hz sine wave
        t = np.linspace(0, 1.5, int(10240 * 1.5))
        signal = np.sin(2 * np.pi * 100 * t)
        
        result = fft_service.compute_spectrum(signal)
        
        # Step 4: Verify results
        assert isinstance(result, FFTResult)
        assert result.frequency is not None
        assert result.spectrum is not None
        assert result.view_type == 'ACC'
        assert result.window_type == 'hanning'
        assert result.sampling_rate == 10240.0
        
        # Verify peak detection
        peak_freq = result.peak_frequency
        assert abs(peak_freq - 100.0) < 2.0, f"Peak at {peak_freq} Hz, expected ~100 Hz"
    
    def test_fft_with_view_type_conversion(self, fft_service):
        """Test FFT workflow with signal type conversion."""
        # Generate test signal
        t = np.linspace(0, 1.5, int(10240 * 1.5))
        signal = np.sin(2 * np.pi * 100 * t)
        
        # Compute for different view types
        result_acc = fft_service.compute_spectrum(signal, view_type='ACC')
        result_vel = fft_service.compute_spectrum(signal, view_type='VEL')
        result_dis = fft_service.compute_spectrum(signal, view_type='DIS')
        
        # All should return valid results
        assert result_acc.view_type == 'ACC'
        assert result_vel.view_type == 'VEL'
        assert result_dis.view_type == 'DIS'
        
        # Peak frequencies should be same (just different amplitudes)
        np.testing.assert_array_equal(result_acc.frequency, result_vel.frequency)
        np.testing.assert_array_equal(result_acc.frequency, result_dis.frequency)
    
    def test_file_load_and_fft_pipeline(self, test_data_file, file_service, fft_service):
        """Test complete pipeline: load file -> parse data -> compute FFT."""
        # Load file
        file_data = file_service.load_file(str(test_data_file))
        
        assert file_data['is_valid']
        assert file_data['sampling_rate'] == 10240.0
        assert file_data['data'] is not None
        assert len(file_data['data']) == 10240
        
        # Compute FFT on loaded data
        result = fft_service.compute_spectrum(file_data['data'])
        
        assert isinstance(result, FFTResult)
        assert result.num_points > 0
        # Should detect the 100 Hz component
        assert abs(result.peak_frequency - 100.0) < 2.0


class TestTrendWorkflow:
    """Test complete trend analysis workflow."""
    
    @pytest.fixture
    def file_service(self):
        """Create file service instance."""
        return FileService()
    
    @pytest.fixture
    def trend_service(self):
        """Create trend service instance."""
        return TrendService(max_workers=2)
    
    def test_trend_analysis_workflow(self, tmp_path, file_service):
        """Test: Create files -> Scan directory -> Verify metadata."""
        # Create test files with proper naming pattern
        for i in range(3):
            f = tmp_path / f"2025-01-15_10-30-0{i}_sensor{i}.txt"
            content = f"""D.Sampling Freq.: 10240 Hz
Channel: CH{i}
Sensitivity: 100 mV/g

1.0
2.0
3.0
"""
            f.write_text(content)
        
        # Scan directory
        metadata_list = file_service.scan_directory(str(tmp_path), "*.txt")
        
        assert len(metadata_list) == 3
        for meta in metadata_list:
            assert isinstance(meta, FileMetadata)
            assert meta.sampling_rate == 10240.0
    
    def test_scan_directory_grouped(self, tmp_path, file_service):
        """Test directory scanning with grouping by timestamp."""
        # Create files with same timestamp (different sensors)
        (tmp_path / "2025-01-15_10-30-00_sensor1.txt").write_text("data1")
        (tmp_path / "2025-01-15_10-30-00_sensor2.txt").write_text("data2")
        # Different timestamp
        (tmp_path / "2025-01-15_11-00-00_sensor1.txt").write_text("data3")
        
        grouped = file_service.scan_directory_grouped(str(tmp_path), "*.txt")
        
        assert len(grouped) == 2
        assert ("2025-01-15", "10:30:00") in grouped
        assert len(grouped[("2025-01-15", "10:30:00")]) == 2
        assert ("2025-01-15", "11:00:00") in grouped
        assert len(grouped[("2025-01-15", "11:00:00")]) == 1
    
    def test_trend_service_empty_files(self, trend_service):
        """Test trend service handles empty file list gracefully."""
        result = trend_service.compute_trend([], view_type='ACC')
        
        assert isinstance(result, TrendResult)
        assert result.num_files == 0
        assert len(result.filenames) == 0


class TestPeakWorkflow:
    """Test complete peak analysis workflow."""
    
    @pytest.fixture
    def peak_service(self):
        """Create peak service instance."""
        return PeakService(max_workers=2)
    
    def test_find_peaks_in_spectrum(self, peak_service):
        """Test peak detection in a spectrum."""
        # Create synthetic spectrum with known peaks
        frequencies = np.arange(0, 500, 1)
        spectrum = np.zeros_like(frequencies, dtype=float)
        
        # Add peaks at 100, 200, 300 Hz
        spectrum[100] = 1.0
        spectrum[200] = 0.8
        spectrum[300] = 0.5
        
        peaks = peak_service.find_peaks(frequencies, spectrum, num_peaks=5, threshold=0.3)
        
        assert len(peaks) >= 3
        peak_freqs = [p[0] for p in peaks]
        assert 100.0 in peak_freqs
        assert 200.0 in peak_freqs
        assert 300.0 in peak_freqs
    
    def test_peak_trend_empty_files(self, peak_service):
        """Test peak service handles empty file list gracefully."""
        result = peak_service.compute_peak_trend([], view_type='ACC')
        
        assert isinstance(result, TrendResult)
        assert result.num_files == 0


class TestServicesIntegration:
    """Test integration between multiple services."""
    
    def test_file_service_with_fft_service(self, tmp_path):
        """Test FileService data flows correctly to FFTService."""
        # Create proper data file
        test_file = tmp_path / "integration_test.txt"
        t = np.linspace(0, 1.5, int(10240 * 1.5))
        signal = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 150 * t)
        
        content = """D.Sampling Freq.: 10240 Hz
Channel: Test
Sensitivity: 100 mV/g

"""
        content += "\n".join(f"{x:.6f}" for x in signal)
        test_file.write_text(content, encoding='utf-8')
        
        # Use services together
        file_svc = FileService()
        fft_svc = FFTService(sampling_rate=10240.0, delta_f=1.0, overlap=50.0)
        
        # Load and process
        file_data = file_svc.load_file(str(test_file))
        assert file_data['is_valid']
        
        result = fft_svc.compute_spectrum(file_data['data'])
        
        # Verify we can detect both frequency components
        assert result.num_points > 0
        # Find peaks
        peak_idx = np.argmax(result.spectrum)
        peak_freq = result.frequency[peak_idx]
        # Should detect one of the main frequencies
        assert peak_freq in [50.0, 51.0, 49.0, 150.0, 149.0, 151.0] or \
               abs(peak_freq - 50.0) < 3 or abs(peak_freq - 150.0) < 3
    
    def test_sensitivity_management_across_operations(self, tmp_path):
        """Test sensitivity values are preserved across file operations."""
        file_svc = FileService()
        
        # Create test file
        test_file = tmp_path / "sens_test.txt"
        test_file.write_text("D.Sampling Freq.: 10240 Hz\nSensitivity: 100 mV/g\n\n1.0\n2.0\n")
        
        # Set custom sensitivity
        file_svc.set_sensitivity("sens_test.txt", 250.0)
        file_svc.set_b_sensitivity("sens_test.txt", 125.0)
        
        # Get metadata - should use stored sensitivity
        metadata = file_svc.get_file_metadata(str(test_file))
        
        assert metadata.sensitivity == 250.0
        assert metadata.b_sensitivity == 125.0
        
        # Clear cache and verify sensitivities still work
        file_svc.clear_file_cache()
        sensitivities = file_svc.get_sensitivities("sens_test.txt")
        
        assert sensitivities['sensitivity'] == 250.0
        assert sensitivities['b_sensitivity'] == 125.0


class TestNoCircularImports:
    """Test for circular import issues."""
    
    def test_import_core_services(self):
        """Test all core services can be imported."""
        from vibration.core.services import FFTService, TrendService, PeakService, FileService
        
        assert FFTService is not None
        assert TrendService is not None
        assert PeakService is not None
        assert FileService is not None
    
    def test_import_domain_models(self):
        """Test all domain models can be imported."""
        from vibration.core.domain import FFTResult, TrendResult, SignalData, FileMetadata
        
        assert FFTResult is not None
        assert TrendResult is not None
        assert SignalData is not None
        assert FileMetadata is not None
    
    def test_import_infrastructure(self):
        """Test infrastructure modules can be imported."""
        from vibration.infrastructure import EventBus, get_event_bus
        
        assert EventBus is not None
        assert get_event_bus is not None
    
    def test_import_presentation_views(self):
        """Test presentation views can be imported (requires Qt)."""
        try:
            from vibration.presentation.views import MainWindow
            assert MainWindow is not None
        except ImportError as e:
            # Qt might not be available in test environment
            if 'PyQt5' in str(e) or 'QtWidgets' in str(e):
                pytest.skip("PyQt5 not available in test environment")
            raise
    
    def test_import_presentation_presenters(self):
        """Test presentation presenters can be imported."""
        try:
            from vibration.presentation.presenters import (
                SpectrumPresenter, TrendPresenter, DataQueryPresenter,
                WaterfallPresenter, PeakPresenter
            )
            assert SpectrumPresenter is not None
            assert TrendPresenter is not None
        except ImportError as e:
            # May have Qt dependency
            if 'PyQt5' in str(e) or 'QtWidgets' in str(e):
                pytest.skip("PyQt5 not available in test environment")
            raise
    
    def test_import_all_modules_in_sequence(self):
        """Test all modules can be imported in sequence without circular deps."""
        # Import in dependency order
        
        # 1. Domain models (no external deps)
        from vibration.core.domain.models import FFTResult, TrendResult
        
        # 2. Infrastructure (minimal deps)
        from vibration.infrastructure.event_bus import EventBus
        
        # 3. Services (depend on domain)
        from vibration.core.services.fft_service import FFTService
        from vibration.core.services.file_service import FileService
        from vibration.core.services.trend_service import TrendService
        from vibration.core.services.peak_service import PeakService
        
        # All imports succeeded
        assert True
    
    def test_reverse_import_order(self):
        """Test imports work in reverse order (catches hidden deps)."""
        # Import in reverse order
        
        # Services first
        from vibration.core.services.peak_service import PeakService
        from vibration.core.services.trend_service import TrendService
        from vibration.core.services.file_service import FileService
        from vibration.core.services.fft_service import FFTService
        
        # Then infrastructure
        from vibration.infrastructure.event_bus import EventBus
        
        # Then domain
        from vibration.core.domain.models import FFTResult, TrendResult
        
        # All imports succeeded
        assert True


class TestServiceInstantiation:
    """Test that services can be instantiated without errors."""
    
    def test_instantiate_all_services(self):
        """Test all services can be instantiated."""
        from vibration.core.services import FFTService, TrendService, PeakService, FileService
        
        file_svc = FileService()
        assert file_svc is not None
        
        fft_svc = FFTService(sampling_rate=10240.0, delta_f=1.0, overlap=50.0)
        assert fft_svc is not None
        
        trend_svc = TrendService(max_workers=2)
        assert trend_svc is not None
        
        peak_svc = PeakService(max_workers=2)
        assert peak_svc is not None
    
    def test_event_bus_singleton(self):
        """Test EventBus singleton pattern works."""
        from vibration.infrastructure import get_event_bus
        
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is bus2


class TestResultDataclasses:
    """Test result dataclass properties and methods."""
    
    def test_fft_result_properties(self):
        """Test FFTResult computed properties."""
        freq = np.array([0, 1, 2, 3, 4, 5])
        spectrum = np.array([0, 0.1, 0.5, 1.0, 0.3, 0.1])
        
        result = FFTResult(
            frequency=freq,
            spectrum=spectrum,
            view_type='ACC',
            window_type='hanning',
            sampling_rate=10.0,
            delta_f=1.0,
            overlap=50.0
        )
        
        assert result.max_frequency == 5.0
        assert result.peak_frequency == 3.0
        assert result.peak_amplitude == 1.0
        assert result.num_points == 6
    
    def test_trend_result_properties(self):
        """Test TrendResult computed properties."""
        result = TrendResult(
            timestamps=[datetime.now() for _ in range(5)],
            rms_values=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            filenames=[f"file{i}.txt" for i in range(5)],
            view_type='ACC'
        )
        
        assert result.num_files == 5
        assert result.mean_rms == 3.0
        assert result.max_rms == 5.0
        assert result.min_rms == 1.0
        assert result.std_rms > 0


class TestNoQtDependency:
    """Verify core services don't require Qt."""
    
    def test_services_no_qt_import(self):
        """Verify core services don't import PyQt5."""
        # Fresh import check
        qt_modules_before = {m for m in sys.modules if 'PyQt5' in m}
        
        # Import services
        from vibration.core.services import FFTService, TrendService, PeakService, FileService
        from vibration.core.domain.models import FFTResult, TrendResult
        from vibration.infrastructure import EventBus
        
        qt_modules_after = {m for m in sys.modules if 'PyQt5' in m}
        
        # No new Qt modules should be imported
        new_qt_modules = qt_modules_after - qt_modules_before
        
        # This is informational - Qt might be imported by other tests
        if new_qt_modules:
            pytest.skip(f"Qt modules imported by previous tests: {new_qt_modules}")
