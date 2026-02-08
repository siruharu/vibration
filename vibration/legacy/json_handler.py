"""
JSON 직렬화/역직렬화 모듈
- NumPy array 자동 변환
- datetime 객체 처리
- 하위 호환성 보장
"""

import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    확장된 JSON 인코더
    - NumPy 타입 자동 변환
    - datetime 객체 ISO 포맷 변환
    - 커스텀 클래스 __dict__ 직렬화
    """
    
    def default(self, obj):
        # NumPy 배열
        if isinstance(obj, np.ndarray):
            return {
                '__ndarray__': obj.tolist(),
                'dtype': str(obj.dtype),
                'shape': obj.shape
            }
        
        # NumPy 스칼라 타입들
        elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        
        elif isinstance(obj, np.bool_):
            return bool(obj)
        
        elif isinstance(obj, np.complexfloating):
            return {'real': obj.real, 'imag': obj.imag}
        
        # datetime 객체
        elif isinstance(obj, datetime):
            return {
                '__datetime__': obj.isoformat()
            }
        
        # Path 객체
        elif isinstance(obj, Path):
            return str(obj)
        
        # 커스텀 클래스 (hasattr로 체크)
        elif hasattr(obj, '__dict__'):
            return {
                '__class__': obj.__class__.__name__,
                'data': obj.__dict__
            }
        
        # 기본 인코더로 fallback
        return super().default(obj)


class EnhancedJSONDecoder(json.JSONDecoder):
    """
    확장된 JSON 디코더
    - NumPy array 복원
    - datetime 객체 복원
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
    
    @staticmethod
    def object_hook(obj):
        # NumPy 배열 복원
        if '__ndarray__' in obj:
            return np.array(
                obj['__ndarray__'],
                dtype=np.dtype(obj['dtype'])
            ).reshape(obj['shape'])
        
        # datetime 복원
        elif '__datetime__' in obj:
            return datetime.fromisoformat(obj['__datetime__'])
        
        return obj


class AnalysisDataManager:
    """
    분석 데이터 저장/로드 관리자
    - Trend → Detail 전환 시 사용
    - 버전 관리 및 하위 호환성 보장
    """
    
    VERSION = "2.0"  # 데이터 포맷 버전
    
    @staticmethod
    def save_analysis_result(data: Dict, filepath: Union[str, Path], 
                            indent: int = 2, ensure_ascii: bool = False) -> bool:
        """
        분석 결과 저장 (에러 발생 안 함)
        
        Args:
            data: 저장할 데이터 (NumPy array 포함 가능)
            filepath: 저장 경로
            indent: JSON 들여쓰기
            ensure_ascii: ASCII 강제 여부 (False = 한글 그대로)
        
        Returns:
            성공 여부
        """
        try:
            # 버전 정보 추가
            data_with_version = {
                'version': AnalysisDataManager.VERSION,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    data_with_version,
                    f,
                    cls=EnhancedJSONEncoder,
                    indent=indent,
                    ensure_ascii=ensure_ascii
                )
            
            logger.info(f"분석 결과 저장 완료: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"분석 결과 저장 실패: {e}")
            return False
    
    @staticmethod
    def load_analysis_result(filepath: Union[str, Path]) -> Dict:
        """
        분석 결과 로드 (구 버전 자동 변환)
        
        Args:
            filepath: 로드할 파일 경로
        
        Returns:
            분석 데이터 딕셔너리
        """
        try:
            filepath = Path(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f, cls=EnhancedJSONDecoder)
            
            # 버전 확인 및 변환
            if 'version' in loaded_data:
                version = loaded_data['version']
                data = loaded_data['data']
                
                if version == "1.0":
                    # 구 버전 데이터 변환
                    data = AnalysisDataManager._convert_from_v1(data)
                
                logger.info(f"분석 결과 로드 완료: {filepath} (버전 {version})")
                return data
            else:
                # 버전 정보 없는 레거시 데이터
                logger.warning(f"레거시 데이터 감지: {filepath}")
                return AnalysisDataManager._convert_legacy(loaded_data)
                
        except FileNotFoundError:
            logger.error(f"파일 없음: {filepath}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 에러: {e}")
            return {}
        except Exception as e:
            logger.error(f"분석 결과 로드 실패: {e}")
            return {}
    
    @staticmethod
    def _convert_from_v1(data: Dict) -> Dict:
        """
        버전 1.0 → 2.0 변환 로직
        """
        # 필요한 필드 추가/변경
        if 'fft_result' in data and isinstance(data['fft_result'], list):
            # list를 numpy array로 변환
            data['fft_result'] = np.array(data['fft_result'])
        
        return data
    
    @staticmethod
    def _convert_legacy(data: Dict) -> Dict:
        """
        레거시 데이터 (버전 정보 없음) 변환
        """
        # 기본 변환 로직
        converted = {}
        
        for key, value in data.items():
            if isinstance(value, list):
                # 숫자 리스트 → numpy array 시도
                try:
                    if all(isinstance(x, (int, float)) for x in value):
                        converted[key] = np.array(value)
                    else:
                        converted[key] = value
                except:
                    converted[key] = value
            else:
                converted[key] = value
        
        return converted


# 편의 함수들 (기존 코드 호환성)
def save_json(data: Any, filepath: str, **kwargs) -> bool:
    """
    간편한 JSON 저장 함수
    
    기존 코드:
        with open(path, 'w') as f:
            json.dump(data, f)  # NumPy array 에러!
    
    개선 코드:
        from json_handler import save_json
        save_json(data, path)  # NumPy array 자동 처리
    """
    return AnalysisDataManager.save_analysis_result(data, filepath, **kwargs)


def load_json(filepath: str) -> Dict:
    """
    간편한 JSON 로드 함수
    
    기존 코드:
        with open(path, 'r') as f:
            data = json.load(f)
    
    개선 코드:
        from json_handler import load_json
        data = load_json(path)  # NumPy array 자동 복원
    """
    return AnalysisDataManager.load_analysis_result(filepath)


# Trend → Detail 전환용 특화 함수
class TrendDetailBridge:
    """
    Trend 분석 → Detail 분석 데이터 전달 브릿지
    """
    
    @staticmethod
    def save_trend_selection(selected_data: Dict, output_path: str) -> bool:
        """
        Trend에서 선택한 데이터를 Detail용으로 저장
        
        Args:
            selected_data: {
                'filename': str,
                'time_range': tuple,
                'frequency_range': tuple,
                'fft_data': np.ndarray,
                'metadata': dict
            }
        """
        # 필수 필드 검증
        required_fields = ['filename', 'fft_data']
        for field in required_fields:
            if field not in selected_data:
                logger.error(f"필수 필드 누락: {field}")
                return False
        
        return save_json(selected_data, output_path)
    
    @staticmethod
    def load_for_detail_analysis(input_path: str) -> Dict:
        """
        Detail 분석용 데이터 로드
        
        Returns:
            Trend에서 선택된 데이터 (numpy array 복원됨)
        """
        data = load_json(input_path)
        
        # 데이터 검증
        if not data:
            logger.error("데이터 로드 실패 또는 비어있음")
            return {}
        
        # FFT 데이터 검증
        if 'fft_data' in data and not isinstance(data['fft_data'], np.ndarray):
            logger.warning("FFT 데이터가 NumPy array가 아님, 변환 시도")
            try:
                data['fft_data'] = np.array(data['fft_data'])
            except:
                logger.error("FFT 데이터 변환 실패")
                return {}
        
        return data


if __name__ == "__main__":
    # 테스트 코드
    
    # NumPy array 포함 데이터 테스트
    test_data = {
        'filename': 'test.wav',
        'fft_result': np.random.rand(1024, 512),  # NumPy array
        'timestamp': datetime.now(),
        'sample_rate': 44100,
        'metadata': {
            'author': '테스트',
            'version': 1.0
        }
    }
    
    # 저장
    save_json(test_data, '/tmp/test_analysis.json')
    print("✓ 저장 완료")
    
    # 로드
    loaded = load_json('/tmp/test_analysis.json')
    print("✓ 로드 완료")
    
    # 검증
    assert isinstance(loaded['fft_result'], np.ndarray)
    assert loaded['fft_result'].shape == (1024, 512)
    assert isinstance(loaded['timestamp'], datetime)
    print("✓ NumPy array 복원 확인")
    print("✓ datetime 복원 확인")
    
    # Trend → Detail 브릿지 테스트
    trend_data = {
        'filename': 'selected_file.wav',
        'time_range': (0, 10.5),
        'fft_data': np.random.rand(256, 128)
    }
    
    TrendDetailBridge.save_trend_selection(trend_data, '/tmp/trend_to_detail.json')
    detail_data = TrendDetailBridge.load_for_detail_analysis('/tmp/trend_to_detail.json')
    
    assert isinstance(detail_data['fft_data'], np.ndarray)
    print("✓ Trend → Detail 브릿지 테스트 통과")
