"""
File loading and management service.

Wraps FileParser for directory scanning and file metadata extraction.
NO Qt dependencies - pure Python implementation.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from file_parser import FileParser
from vibration.core.domain.models import FileMetadata


class FileService:
    """
    Service layer for file loading and management.
    
    Provides directory scanning, file parsing, and sensitivity management
    without Qt dependencies.
    """
    
    def __init__(self):
        self._sensitivity_map: Dict[str, float] = {}
        self._b_sensitivity_map: Dict[str, float] = {}
        self._file_cache: Dict[str, FileParser] = {}
    
    def scan_directory(
        self,
        directory: str,
        pattern: str = "*.txt"
    ) -> List[FileMetadata]:
        """
        Scan directory for files matching pattern.
        
        Args:
            directory: Directory path to scan.
            pattern: Glob pattern for file matching.
            
        Returns:
            List of FileMetadata objects sorted by filename.
        """
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return []
        
        files = []
        for file_path in sorted(path.glob(pattern)):
            if file_path.is_file():
                metadata = self._extract_metadata(file_path)
                files.append(metadata)
        
        return files
    
    def scan_directory_grouped(
        self,
        directory: str,
        pattern: str = "*.txt"
    ) -> Dict[Tuple[str, str], List[str]]:
        """
        Scan directory and group files by date/time pattern.
        
        Parses filenames with format: YYYY-MM-DD_HH-MM-SS_*.txt
        and groups them by (date, time).
        
        Args:
            directory: Directory path to scan.
            pattern: Glob pattern for file matching.
            
        Returns:
            Dictionary mapping (date, time) tuples to lists of filenames.
        """
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return {}
        
        file_dict: Dict[Tuple[str, str], List[str]] = {}
        
        for file_path in path.glob(pattern):
            if not file_path.is_file():
                continue
            
            filename = file_path.name
            parts = filename.split("_")
            
            if len(parts) >= 2:
                date_part = parts[0]
                time_part = parts[1]
                time_parts = time_part.split("-")
                
                if len(time_parts) == 3:
                    formatted_time = f"{time_parts[0]}:{time_parts[1]}:{time_parts[2]}"
                    key = (date_part, formatted_time)
                    
                    if key not in file_dict:
                        file_dict[key] = []
                    file_dict[key].append(filename)
        
        return file_dict
    
    def load_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load file data using FileParser.
        
        Args:
            filepath: Path to file.
            
        Returns:
            Dictionary with data, sampling_rate, metadata, and validity.
        """
        parser = FileParser(filepath)
        self._file_cache[filepath] = parser
        
        return {
            'data': parser.get_data(),
            'sampling_rate': parser.get_sampling_rate(),
            'record_length': parser.get_record_length(),
            'metadata': parser.get_all_metadata(),
            'is_valid': parser.is_valid()
        }
    
    def load_file_data(self, filepath: str) -> Optional[Any]:
        """
        Load only the signal data from file.
        
        Args:
            filepath: Path to file.
            
        Returns:
            NumPy array of signal data or None if invalid.
        """
        result = self.load_file(filepath)
        if result['is_valid']:
            return result['data']
        return None
    
    def get_file_metadata(self, filepath: str) -> FileMetadata:
        """
        Get metadata for a specific file.
        
        Args:
            filepath: Path to file.
            
        Returns:
            FileMetadata object with file information.
        """
        return self._extract_metadata(Path(filepath))
    
    def set_sensitivity(self, filename: str, sensitivity: float) -> None:
        """Set sensitivity value for a file."""
        self._sensitivity_map[filename] = sensitivity
    
    def get_sensitivity(self, filename: str) -> Optional[float]:
        """Get sensitivity value for a file."""
        return self._sensitivity_map.get(filename)
    
    def set_b_sensitivity(self, filename: str, b_sensitivity: float) -> None:
        """Set B-weighting sensitivity for a file."""
        self._b_sensitivity_map[filename] = b_sensitivity
    
    def get_b_sensitivity(self, filename: str) -> Optional[float]:
        """Get B-weighting sensitivity for a file."""
        return self._b_sensitivity_map.get(filename)
    
    def set_sensitivities(
        self,
        filename: str,
        sensitivity: Optional[float] = None,
        b_sensitivity: Optional[float] = None
    ) -> None:
        """Set both sensitivity values for a file."""
        if sensitivity is not None:
            self._sensitivity_map[filename] = sensitivity
        if b_sensitivity is not None:
            self._b_sensitivity_map[filename] = b_sensitivity
    
    def get_sensitivities(self, filename: str) -> Dict[str, Optional[float]]:
        """Get both sensitivity values for a file."""
        return {
            'sensitivity': self._sensitivity_map.get(filename),
            'b_sensitivity': self._b_sensitivity_map.get(filename)
        }
    
    def clear_sensitivity_cache(self) -> None:
        """Clear all cached sensitivity values."""
        self._sensitivity_map.clear()
        self._b_sensitivity_map.clear()
    
    def clear_file_cache(self) -> None:
        """Clear all cached file parsers."""
        self._file_cache.clear()
    
    def _extract_metadata(self, file_path: Path) -> FileMetadata:
        """Extract metadata from file path and contents."""
        stat = file_path.stat()
        
        mod_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        sampling_rate = 0.0
        sensitivity = None
        b_sensitivity = None
        duration = None
        channel = None
        raw_metadata: Dict[str, Any] = {}
        
        if file_path.suffix.lower() == '.txt':
            try:
                parser = FileParser(str(file_path))
                if parser.is_valid():
                    sampling_rate = parser.get_sampling_rate()
                    raw_metadata = parser.get_all_metadata()
                    
                    sens_str = raw_metadata.get('sensitivity')
                    if sens_str:
                        try:
                            sensitivity = float(sens_str.split()[0])
                        except (ValueError, IndexError):
                            pass
                    
                    b_sens_str = raw_metadata.get('b_sensitivity')
                    if b_sens_str:
                        try:
                            b_sensitivity = float(b_sens_str)
                        except ValueError:
                            pass
                    
                    channel = raw_metadata.get('channel')
                    
                    duration_str = raw_metadata.get('duration')
                    if duration_str:
                        try:
                            duration = float(duration_str)
                        except ValueError:
                            pass
            except Exception:
                pass
        
        stored_sens = self._sensitivity_map.get(file_path.name)
        stored_b_sens = self._b_sensitivity_map.get(file_path.name)
        
        return FileMetadata(
            filename=file_path.name,
            filepath=str(file_path.resolve()),
            size=stat.st_size,
            date_modified=mod_time,
            num_channels=1,
            sampling_rate=sampling_rate,
            sensitivity=stored_sens if stored_sens else sensitivity,
            b_sensitivity=stored_b_sens if stored_b_sens else b_sensitivity,
            duration=duration,
            channel=channel,
            metadata=raw_metadata
        )


if __name__ == "__main__":
    print("FileService Test")
    print("=" * 50)
    
    service = FileService()
    
    service.set_sensitivity("test.txt", 100.0)
    service.set_b_sensitivity("test.txt", 50.0)
    
    assert service.get_sensitivity("test.txt") == 100.0
    assert service.get_b_sensitivity("test.txt") == 50.0
    
    sens = service.get_sensitivities("test.txt")
    assert sens['sensitivity'] == 100.0
    assert sens['b_sensitivity'] == 50.0
    
    service.clear_sensitivity_cache()
    assert service.get_sensitivity("test.txt") is None
    
    print("Sensitivity management: OK")
    
    current_dir = Path(__file__).parent
    files = service.scan_directory(str(current_dir), "*.py")
    print(f"Found {len(files)} Python files in services/")
    
    for f in files[:3]:
        print(f"  - {f.filename}: {f.size_kb:.1f} KB")
    
    print("\nFileService OK")
