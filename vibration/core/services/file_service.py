"""
파일 로딩 및 관리 서비스.

FileParser를 래핑하여 디렉토리 스캔 및 파일 메타데이터 추출을 수행합니다.
Qt 의존성 없음 - 순수 Python 구현.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from .file_parser import FileParser
from vibration.core.domain.models import FileMetadata


class FileService:
    """
    파일 로딩 및 관리를 위한 서비스 레이어.

    Qt 의존성 없이 디렉토리 스캔, 파일 파싱, 감도 관리 기능을 제공합니다.
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
        패턴에 맞는 파일을 디렉토리에서 스캔합니다.

        인자:
            directory: 스캔할 디렉토리 경로.
            pattern: 파일 매칭을 위한 Glob 패턴.

        반환:
            파일명 기준으로 정렬된 FileMetadata 객체 목록.
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
        디렉토리를 스캔하고 날짜/시간 패턴별로 파일을 그룹화합니다.

        YYYY-MM-DD_HH-MM-SS_*.txt 형식의 파일명을 파싱하여
        (날짜, 시간) 기준으로 그룹화합니다.

        인자:
            directory: 스캔할 디렉토리 경로.
            pattern: 파일 매칭을 위한 Glob 패턴.

        반환:
            (날짜, 시간) 튜플을 파일명 목록에 매핑하는 딕셔너리.
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
        FileParser를 사용하여 파일 데이터를 로드합니다.

        인자:
            filepath: 파일 경로.

        반환:
            data, sampling_rate, metadata, validity를 포함하는 딕셔너리.
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
        파일에서 신호 데이터만 로드합니다.

        인자:
            filepath: 파일 경로.

        반환:
            신호 데이터의 NumPy 배열 또는 유효하지 않은 경우 None.
        """
        result = self.load_file(filepath)
        if result['is_valid']:
            return result['data']
        return None
    
    def get_file_metadata(self, filepath: str) -> FileMetadata:
        """
        특정 파일의 메타데이터를 가져옵니다.

        인자:
            filepath: 파일 경로.

        반환:
            파일 정보가 포함된 FileMetadata 객체.
        """
        return self._extract_metadata(Path(filepath))
    
    def set_sensitivity(self, filename: str, sensitivity: float) -> None:
        """파일의 감도 값을 설정합니다."""
        self._sensitivity_map[filename] = sensitivity
    
    def get_sensitivity(self, filename: str) -> Optional[float]:
        """파일의 감도 값을 가져옵니다."""
        return self._sensitivity_map.get(filename)
    
    def set_b_sensitivity(self, filename: str, b_sensitivity: float) -> None:
        """파일의 B 가중 감도를 설정합니다."""
        self._b_sensitivity_map[filename] = b_sensitivity
    
    def get_b_sensitivity(self, filename: str) -> Optional[float]:
        """파일의 B 가중 감도를 가져옵니다."""
        return self._b_sensitivity_map.get(filename)
    
    def set_sensitivities(
        self,
        filename: str,
        sensitivity: Optional[float] = None,
        b_sensitivity: Optional[float] = None
    ) -> None:
        """파일의 두 감도 값을 모두 설정합니다."""
        if sensitivity is not None:
            self._sensitivity_map[filename] = sensitivity
        if b_sensitivity is not None:
            self._b_sensitivity_map[filename] = b_sensitivity
    
    def get_sensitivities(self, filename: str) -> Dict[str, Optional[float]]:
        """파일의 두 감도 값을 모두 가져옵니다."""
        return {
            'sensitivity': self._sensitivity_map.get(filename),
            'b_sensitivity': self._b_sensitivity_map.get(filename)
        }
    
    def clear_sensitivity_cache(self) -> None:
        """캐시된 모든 감도 값을 초기화합니다."""
        self._sensitivity_map.clear()
        self._b_sensitivity_map.clear()
    
    def clear_file_cache(self) -> None:
        """캐시된 모든 파일 파서를 초기화합니다."""
        self._file_cache.clear()
    
    def _extract_metadata(self, file_path: Path) -> FileMetadata:
        """파일 경로와 내용에서 메타데이터를 추출합니다."""
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
