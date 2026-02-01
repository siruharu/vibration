"""
최적화된 파일 로더
- 빠른 데이터 로딩
- 메타데이터 캐싱
- NumPy 벡터화
"""

import numpy as np
import re
from pathlib import Path


class FileParser:
    """최적화된 파일 파서 - 빠른 데이터 로딩 및 메타데이터 추출"""

    def __init__(self, file_path):
        """
        파일 경로로 파서 초기화

        Args:
            file_path (str): 파일 경로
        """
        self.file_path = Path(file_path)
        self._data = None
        self._metadata = {}
        self._record_length = None
        self._parsed = False

        # 파일 로드
        self._load_file()

    def _load_file(self):
        """파일을 한 번에 로드하고 파싱"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 메타데이터와 데이터 분리
            data_start_idx = None

            for i, line in enumerate(lines):
                # 메타데이터 파싱
                if ':' in line and data_start_idx is None:
                    self._parse_metadata_line(line)

                # 데이터 시작 찾기
                if line.strip() and self._is_data_line(line):
                    if data_start_idx is None:
                        data_start_idx = i

            # 데이터 추출 (NumPy로 빠르게)
            if data_start_idx is not None:
                data_lines = lines[data_start_idx:]
                self._data = self._parse_data_fast(data_lines)
                self._record_length = len(self._data)
            else:
                self._data = np.array([])
                self._record_length = 0

            self._parsed = True

        except Exception as e:
            print(f"⚠️ 파일 로드 오류 ({self.file_path}): {e}")
            self._data = np.array([])
            self._record_length = 0
            self._parsed = False

    def _parse_metadata_line(self, line):
        """메타데이터 라인 파싱"""
        try:
            if "D.Sampling Freq." in line:
                value = line.split(":")[1].strip()
                self._metadata['sampling_rate'] = float(value.replace("Hz", "").strip())

            elif "Time Resolution(dt)" in line:
                self._metadata['dt'] = line.split(":")[1].strip()

            elif "Starting Time" in line:
                self._metadata['start_time'] = line.split(":")[1].strip()

            elif "Record Length" in line:
                self._metadata['duration'] = line.split(":")[1].strip().split()[0]

            elif "Rest time" in line:
                self._metadata['rest_time'] = line.split(":")[1].strip().split()[0]

            elif "Repetition" in line:
                self._metadata['repetition'] = line.split(":")[1].strip()

            elif "Channel" in line:
                self._metadata['channel'] = line.split(":")[1].strip()

            elif "IEPE enable" in line:
                self._metadata['iepe'] = line.split(":")[1].strip()

            elif "b.Sensitivity" in line:
                if 'b_sensitivity' not in self._metadata:
                    self._metadata['b_sensitivity'] = line.split(":")[1].strip().split()[0]

            elif "Sensitivity" in line and "b.Sensitivity" not in line:
                self._metadata['sensitivity'] = line.split(":")[1].strip()

        except Exception as e:
            pass  # 메타데이터 파싱 실패는 무시

    def _is_data_line(self, line):
        """데이터 라인인지 확인 (숫자로 시작하는지)"""
        stripped = line.strip()
        if not stripped:
            return False

        # 숫자나 부호로 시작하는지 확인
        return stripped[0].isdigit() or stripped[0] in ['-', '+', '.']

    def _parse_data_fast(self, data_lines):
        """
        NumPy를 사용한 빠른 데이터 파싱

        Args:
            data_lines (list): 데이터 라인 리스트

        Returns:
            np.ndarray: 파싱된 데이터
        """
        try:
            # 빈 라인 제거
            clean_lines = [line.strip() for line in data_lines if line.strip()]

            # NumPy로 한 번에 로드
            data = np.loadtxt(clean_lines, dtype=np.float64)

            return data

        except Exception as e:
            # 실패 시 느린 방법
            print(f"⚠️ NumPy 로드 실패, 수동 파싱: {e}")

            values = []
            for line in data_lines:
                try:
                    stripped = line.strip()
                    if stripped and self._is_data_line(stripped):
                        value = float(stripped)
                        values.append(value)
                except:
                    continue

            return np.array(values, dtype=np.float64)

    def get_data(self):
        """데이터 반환"""
        return self._data

    def get_record_length(self):
        """레코드 길이 반환"""
        return self._record_length

    def get_sampling_rate(self):
        """샘플링 레이트 반환"""
        return self._metadata.get('sampling_rate', 10240.0)

    def get_metadata(self, key):
        """특정 메타데이터 반환"""
        return self._metadata.get(key)

    def get_all_metadata(self):
        """모든 메타데이터 반환"""
        return self._metadata.copy()

    def is_valid(self):
        """파싱 성공 여부"""
        return self._parsed and len(self._data) > 0


# ========================================
# 테스트 코드
# ========================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]

        print(f"🔍 파일 파싱 테스트: {file_path}")
        print("="*60)

        parser = FileParser(file_path)

        print(f"✅ 파싱 성공: {parser.is_valid()}")
        print(f"📊 데이터 개수: {len(parser.get_data())}")
        print(f"📈 샘플링 레이트: {parser.get_sampling_rate()} Hz")
        print(f"⏱️ 레코드 길이: {parser.get_record_length()}")

        print("\n📋 메타데이터:")
        for key, value in parser.get_all_metadata().items():
            print(f"  - {key}: {value}")

        print("\n📊 데이터 샘플 (처음 10개):")
        data = parser.get_data()
        print(data[:10] if len(data) >= 10 else data)

    else:
        print("사용법: python file_loader_optimized.py <파일경로>")