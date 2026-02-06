"""Unit tests for File service."""
import pytest
import sys
from pathlib import Path

from vibration.core.services.file_service import FileService
from vibration.core.domain.models import FileMetadata


class TestFileServiceInit:
    """Tests for FileService initialization."""
    
    def test_init_creates_empty_sensitivity_maps(self):
        """Test that service initializes with empty sensitivity maps."""
        svc = FileService()
        
        assert hasattr(svc, '_sensitivity_map')
        assert hasattr(svc, '_b_sensitivity_map')
        assert hasattr(svc, '_file_cache')
        assert len(svc._sensitivity_map) == 0
        assert len(svc._b_sensitivity_map) == 0
        assert len(svc._file_cache) == 0


@pytest.fixture
def file_service():
    """Create FileService instance."""
    return FileService()


@pytest.fixture
def temp_data_file(tmp_path):
    """Create temporary data file with proper format for FileParser."""
    file_path = tmp_path / "test_data.txt"
    content = """D.Sampling Freq.: 10240 Hz
Channel: CH1
Sensitivity: 100 mV/g
b.Sensitivity: 50
Record Length: 1.0 sec

0.001
0.002
0.003
0.004
0.005
"""
    file_path.write_text(content, encoding='utf-8')
    return file_path


@pytest.fixture
def temp_data_file_minimal(tmp_path):
    """Create minimal data file for basic parsing."""
    file_path = tmp_path / "minimal.txt"
    content = """1.0
2.0
3.0
"""
    file_path.write_text(content, encoding='utf-8')
    return file_path


class TestScanDirectory:
    """Tests for scan_directory method."""
    
    def test_scan_directory_finds_files(self, file_service, tmp_path):
        """Test directory scanning finds matching files."""
        # Create test files
        (tmp_path / "file1.txt").write_text("data1")
        (tmp_path / "file2.txt").write_text("data2")
        (tmp_path / "file3.csv").write_text("csv data")  # Should not match
        
        files = file_service.scan_directory(str(tmp_path), "*.txt")
        
        assert len(files) == 2
        assert all(isinstance(f, FileMetadata) for f in files)
        filenames = [f.filename for f in files]
        assert "file1.txt" in filenames
        assert "file2.txt" in filenames
        assert "file3.csv" not in filenames
    
    def test_scan_directory_returns_sorted_files(self, file_service, tmp_path):
        """Test that scanned files are sorted by filename."""
        (tmp_path / "zebra.txt").write_text("z")
        (tmp_path / "alpha.txt").write_text("a")
        (tmp_path / "beta.txt").write_text("b")
        
        files = file_service.scan_directory(str(tmp_path), "*.txt")
        
        filenames = [f.filename for f in files]
        assert filenames == ["alpha.txt", "beta.txt", "zebra.txt"]
    
    def test_scan_directory_extracts_metadata(self, file_service, tmp_path):
        """Test that metadata is extracted for each file."""
        (tmp_path / "test.txt").write_text("some content here")
        
        files = file_service.scan_directory(str(tmp_path), "*.txt")
        
        assert len(files) == 1
        metadata = files[0]
        assert metadata.filename == "test.txt"
        assert metadata.size > 0
        assert metadata.date_modified is not None
        assert str(tmp_path) in metadata.filepath
    
    def test_scan_directory_with_custom_pattern(self, file_service, tmp_path):
        """Test scanning with custom glob pattern."""
        (tmp_path / "data.csv").write_text("csv")
        (tmp_path / "data.txt").write_text("txt")
        
        files = file_service.scan_directory(str(tmp_path), "*.csv")
        
        assert len(files) == 1
        assert files[0].filename == "data.csv"
    
    def test_scan_directory_excludes_subdirectories(self, file_service, tmp_path):
        """Test that subdirectories are not included in results."""
        (tmp_path / "file.txt").write_text("data")
        subdir = tmp_path / "subdir.txt"  # Directory with .txt extension
        subdir.mkdir()
        
        files = file_service.scan_directory(str(tmp_path), "*.txt")
        
        assert len(files) == 1
        assert files[0].filename == "file.txt"


class TestScanDirectoryGrouped:
    """Tests for scan_directory_grouped method."""
    
    def test_groups_files_by_date_time(self, file_service, tmp_path):
        """Test that files are grouped by date/time pattern."""
        # Create files with date-time naming pattern
        (tmp_path / "2025-01-15_10-30-00_sensor1.txt").write_text("data")
        (tmp_path / "2025-01-15_10-30-00_sensor2.txt").write_text("data")
        (tmp_path / "2025-01-15_11-00-00_sensor1.txt").write_text("data")
        
        grouped = file_service.scan_directory_grouped(str(tmp_path), "*.txt")
        
        assert len(grouped) == 2
        assert ("2025-01-15", "10:30:00") in grouped
        assert ("2025-01-15", "11:00:00") in grouped
        assert len(grouped[("2025-01-15", "10:30:00")]) == 2
        assert len(grouped[("2025-01-15", "11:00:00")]) == 1
    
    def test_handles_non_matching_filenames(self, file_service, tmp_path):
        """Test that non-matching filenames are ignored."""
        (tmp_path / "random_file.txt").write_text("data")
        (tmp_path / "2025-01-15_10-30-00_sensor.txt").write_text("data")
        
        grouped = file_service.scan_directory_grouped(str(tmp_path), "*.txt")
        
        # random_file.txt won't have proper time format
        assert ("2025-01-15", "10:30:00") in grouped


class TestLoadFile:
    """Tests for load_file method."""
    
    def test_load_file_returns_data_dict(self, file_service, temp_data_file):
        """Test that load_file returns dictionary with expected keys."""
        result = file_service.load_file(str(temp_data_file))
        
        assert isinstance(result, dict)
        assert 'data' in result
        assert 'sampling_rate' in result
        assert 'record_length' in result
        assert 'metadata' in result
        assert 'is_valid' in result
    
    def test_load_file_extracts_sampling_rate(self, file_service, temp_data_file):
        """Test that sampling rate is extracted from file."""
        result = file_service.load_file(str(temp_data_file))
        
        assert result['sampling_rate'] == 10240.0
    
    def test_load_file_extracts_data(self, file_service, temp_data_file):
        """Test that data array is extracted."""
        result = file_service.load_file(str(temp_data_file))
        
        assert result['data'] is not None
        assert len(result['data']) == 5
    
    def test_load_file_caches_parser(self, file_service, temp_data_file):
        """Test that file parser is cached."""
        file_path = str(temp_data_file)
        
        file_service.load_file(file_path)
        
        assert file_path in file_service._file_cache
    
    def test_load_file_metadata_contains_channel(self, file_service, temp_data_file):
        """Test that metadata contains channel information."""
        result = file_service.load_file(str(temp_data_file))
        
        assert result['metadata'].get('channel') == 'CH1'


class TestLoadFileData:
    """Tests for load_file_data method."""
    
    def test_load_file_data_returns_array(self, file_service, temp_data_file):
        """Test that load_file_data returns numpy array."""
        data = file_service.load_file_data(str(temp_data_file))
        
        assert data is not None
        assert len(data) == 5
    
    def test_load_file_data_invalid_file_returns_none(self, file_service, tmp_path):
        """Test that invalid file returns None."""
        # Create empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        
        data = file_service.load_file_data(str(empty_file))
        
        # Empty file may return None or empty array
        assert data is None or len(data) == 0


class TestGetFileMetadata:
    """Tests for get_file_metadata method."""
    
    def test_get_file_metadata_returns_dataclass(self, file_service, temp_data_file):
        """Test that get_file_metadata returns FileMetadata."""
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert isinstance(metadata, FileMetadata)
    
    def test_get_file_metadata_extracts_filename(self, file_service, temp_data_file):
        """Test that filename is extracted."""
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert metadata.filename == "test_data.txt"
    
    def test_get_file_metadata_extracts_size(self, file_service, temp_data_file):
        """Test that file size is extracted."""
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert metadata.size > 0
        assert metadata.size_kb > 0
    
    def test_get_file_metadata_extracts_sampling_rate(self, file_service, temp_data_file):
        """Test that sampling rate is extracted from file content."""
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert metadata.sampling_rate == 10240.0
    
    def test_get_file_metadata_extracts_channel(self, file_service, temp_data_file):
        """Test that channel is extracted."""
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert metadata.channel == "CH1"


class TestSensitivityManagement:
    """Tests for sensitivity management methods."""
    
    def test_set_and_get_sensitivity(self, file_service):
        """Test setting and getting sensitivity."""
        file_service.set_sensitivity("test.txt", 100.0)
        
        assert file_service.get_sensitivity("test.txt") == 100.0
    
    def test_get_sensitivity_nonexistent_returns_none(self, file_service):
        """Test that getting sensitivity for unknown file returns None."""
        result = file_service.get_sensitivity("nonexistent.txt")
        
        assert result is None
    
    def test_set_and_get_b_sensitivity(self, file_service):
        """Test setting and getting B-weighting sensitivity."""
        file_service.set_b_sensitivity("test.txt", 50.0)
        
        assert file_service.get_b_sensitivity("test.txt") == 50.0
    
    def test_get_b_sensitivity_nonexistent_returns_none(self, file_service):
        """Test that getting B-sensitivity for unknown file returns None."""
        result = file_service.get_b_sensitivity("nonexistent.txt")
        
        assert result is None
    
    def test_set_sensitivities_both(self, file_service):
        """Test setting both sensitivities at once."""
        file_service.set_sensitivities("test.txt", sensitivity=100.0, b_sensitivity=50.0)
        
        assert file_service.get_sensitivity("test.txt") == 100.0
        assert file_service.get_b_sensitivity("test.txt") == 50.0
    
    def test_set_sensitivities_partial(self, file_service):
        """Test setting only one sensitivity via set_sensitivities."""
        file_service.set_sensitivities("test.txt", sensitivity=100.0)
        
        assert file_service.get_sensitivity("test.txt") == 100.0
        assert file_service.get_b_sensitivity("test.txt") is None
    
    def test_get_sensitivities_returns_dict(self, file_service):
        """Test that get_sensitivities returns dictionary."""
        file_service.set_sensitivity("test.txt", 100.0)
        file_service.set_b_sensitivity("test.txt", 50.0)
        
        result = file_service.get_sensitivities("test.txt")
        
        assert isinstance(result, dict)
        assert result['sensitivity'] == 100.0
        assert result['b_sensitivity'] == 50.0
    
    def test_get_sensitivities_unknown_file(self, file_service):
        """Test get_sensitivities for unknown file."""
        result = file_service.get_sensitivities("unknown.txt")
        
        assert result['sensitivity'] is None
        assert result['b_sensitivity'] is None
    
    def test_clear_sensitivity_cache(self, file_service):
        """Test clearing sensitivity cache."""
        file_service.set_sensitivity("file1.txt", 100.0)
        file_service.set_b_sensitivity("file2.txt", 50.0)
        
        file_service.clear_sensitivity_cache()
        
        assert file_service.get_sensitivity("file1.txt") is None
        assert file_service.get_b_sensitivity("file2.txt") is None
    
    def test_sensitivity_overwrite(self, file_service):
        """Test overwriting sensitivity value."""
        file_service.set_sensitivity("test.txt", 100.0)
        file_service.set_sensitivity("test.txt", 200.0)
        
        assert file_service.get_sensitivity("test.txt") == 200.0
    
    def test_multiple_files_sensitivity(self, file_service):
        """Test managing sensitivities for multiple files."""
        file_service.set_sensitivity("file1.txt", 100.0)
        file_service.set_sensitivity("file2.txt", 150.0)
        file_service.set_sensitivity("file3.txt", 200.0)
        
        assert file_service.get_sensitivity("file1.txt") == 100.0
        assert file_service.get_sensitivity("file2.txt") == 150.0
        assert file_service.get_sensitivity("file3.txt") == 200.0


class TestCacheManagement:
    """Tests for cache management methods."""
    
    def test_clear_file_cache(self, file_service, temp_data_file):
        """Test clearing file cache."""
        file_service.load_file(str(temp_data_file))
        
        assert len(file_service._file_cache) > 0
        
        file_service.clear_file_cache()
        
        assert len(file_service._file_cache) == 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_scan_nonexistent_directory_returns_empty(self, file_service):
        """Test scanning nonexistent directory returns empty list."""
        files = file_service.scan_directory("/nonexistent/path/xyz")
        
        assert len(files) == 0
        assert isinstance(files, list)
    
    def test_scan_file_as_directory_returns_empty(self, file_service, temp_data_file):
        """Test scanning a file path (not directory) returns empty."""
        files = file_service.scan_directory(str(temp_data_file))
        
        assert len(files) == 0
    
    def test_scan_empty_directory_returns_empty(self, file_service, tmp_path):
        """Test scanning empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        files = file_service.scan_directory(str(empty_dir), "*.txt")
        
        assert len(files) == 0
    
    def test_scan_directory_grouped_nonexistent_returns_empty(self, file_service):
        """Test scan_directory_grouped on nonexistent directory."""
        result = file_service.scan_directory_grouped("/nonexistent/path")
        
        assert result == {}
    
    def test_scan_directory_no_matching_files(self, file_service, tmp_path):
        """Test scanning directory with no matching files."""
        (tmp_path / "data.csv").write_text("csv data")
        
        files = file_service.scan_directory(str(tmp_path), "*.txt")
        
        assert len(files) == 0
    
    def test_sensitivity_with_special_characters(self, file_service):
        """Test sensitivity with filename containing special characters."""
        filename = "file with spaces & (special).txt"
        file_service.set_sensitivity(filename, 100.0)
        
        assert file_service.get_sensitivity(filename) == 100.0
    
    def test_sensitivity_with_negative_value(self, file_service):
        """Test setting negative sensitivity value."""
        file_service.set_sensitivity("test.txt", -100.0)
        
        assert file_service.get_sensitivity("test.txt") == -100.0
    
    def test_sensitivity_with_zero_value(self, file_service):
        """Test setting zero sensitivity value."""
        file_service.set_sensitivity("test.txt", 0.0)
        
        assert file_service.get_sensitivity("test.txt") == 0.0
    
    def test_sensitivity_with_float_precision(self, file_service):
        """Test sensitivity with high precision float."""
        file_service.set_sensitivity("test.txt", 100.123456789)
        
        assert file_service.get_sensitivity("test.txt") == 100.123456789


class TestStoredSensitivityInMetadata:
    """Tests for stored sensitivity appearing in metadata."""
    
    def test_stored_sensitivity_used_in_metadata(self, file_service, temp_data_file):
        """Test that stored sensitivity overrides file sensitivity."""
        file_service.set_sensitivity("test_data.txt", 999.0)
        
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert metadata.sensitivity == 999.0
    
    def test_stored_b_sensitivity_used_in_metadata(self, file_service, temp_data_file):
        """Test that stored B-sensitivity overrides file value."""
        file_service.set_b_sensitivity("test_data.txt", 888.0)
        
        metadata = file_service.get_file_metadata(str(temp_data_file))
        
        assert metadata.b_sensitivity == 888.0


class TestNoQtDependency:
    """Verify tests don't import Qt."""
    
    def test_no_pyqt5_import(self):
        """Verify PyQt5 is not imported by the test module."""
        assert 'PyQt5' not in sys.modules, "PyQt5 should not be imported in unit tests"
        assert 'PyQt5.QtWidgets' not in sys.modules
        assert 'PyQt5.QtCore' not in sys.modules
