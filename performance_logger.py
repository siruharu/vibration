"""
성능 측정 및 로깅 모듈
- 파일 로딩, FFT 계산, 테이블 렌더링 등의 시간 측정
- Before/After 비교
- 자동 로그 파일 생성
"""

import time
import logging
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Callable, Any, Dict, List
import json


class PerformanceLogger:
    """
    성능 측정 로거
    - 함수 실행 시간 자동 측정
    - 비교 리포트 생성
    """
    
    def __init__(self, log_file: str = None, console_output: bool = True):
        """
        Args:
            log_file: 로그 파일 경로 (None이면 자동 생성)
            console_output: 콘솔 출력 여부
        """
        # 로그 파일명 생성
        if log_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"performance_log_{timestamp}.txt"
        
        self.log_file = Path(log_file)
        self.console_output = console_output
        
        # 측정 데이터 저장
        self.measurements: Dict[str, List[float]] = {}
        self.comparison_data: Dict[str, Dict] = {}
        
        # 로거 설정
        self.logger = self._setup_logger()
        
        # 시작 시간
        self.session_start = time.time()
        
        self.log_info("="*60)
        self.log_info("성능 측정 시작")
        self.log_info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_info("="*60)
    
    def _setup_logger(self):
        """로거 초기화"""
        logger = logging.getLogger('PerformanceLogger')
        logger.setLevel(logging.INFO)
        
        # 파일 핸들러
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        # 콘솔 핸들러 (선택)
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def log_info(self, message: str):
        """정보 로그"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """경고 로그"""
        self.logger.warning(message)
    
    def measure_time(self, operation_name: str):
        """
        시간 측정 데코레이터
        
        사용법:
            @perf_logger.measure_time("파일 로딩")
            def load_files(files):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                self.log_info(f"\n▶ {operation_name} 시작...")
                
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    
                    # 측정 데이터 저장
                    if operation_name not in self.measurements:
                        self.measurements[operation_name] = []
                    self.measurements[operation_name].append(elapsed)
                    
                    # 로그 출력
                    self.log_info(f"✓ {operation_name} 완료: {elapsed:.3f}초")
                    
                    return result
                    
                except Exception as e:
                    elapsed = time.time() - start_time
                    self.log_warning(f"✗ {operation_name} 실패 ({elapsed:.3f}초): {e}")
                    raise
            
            return wrapper
        return decorator
    
    def start_timer(self, operation_name: str) -> float:
        """
        수동 타이머 시작
        
        Returns:
            시작 시간 (time.time())
        """
        self.log_info(f"\n▶ {operation_name} 시작...")
        return time.time()
    
    def end_timer(self, operation_name: str, start_time: float):
        """
        수동 타이머 종료
        
        Args:
            operation_name: 작업 이름
            start_time: start_timer()의 반환값
        """
        elapsed = time.time() - start_time
        
        # 측정 데이터 저장
        if operation_name not in self.measurements:
            self.measurements[operation_name] = []
        self.measurements[operation_name].append(elapsed)
        
        self.log_info(f"✓ {operation_name} 완료: {elapsed:.3f}초")
        
        return elapsed
    
    def compare(self, operation_name: str, old_time: float, new_time: float):
        """
        Before/After 비교
        
        Args:
            operation_name: 작업 이름
            old_time: 기존 시간
            new_time: 새 시간
        """
        speedup = old_time / new_time if new_time > 0 else 0
        improvement = ((old_time - new_time) / old_time * 100) if old_time > 0 else 0
        
        self.comparison_data[operation_name] = {
            'old': old_time,
            'new': new_time,
            'speedup': speedup,
            'improvement': improvement
        }
        
        self.log_info(f"\n📊 {operation_name} 비교:")
        self.log_info(f"   기존: {old_time:.3f}초")
        self.log_info(f"   최적화: {new_time:.3f}초")
        self.log_info(f"   속도 향상: {speedup:.1f}배")
        self.log_info(f"   개선율: {improvement:.1f}%")
    
    def generate_summary(self):
        """최종 요약 리포트 생성"""
        session_elapsed = time.time() - self.session_start
        
        self.log_info("\n" + "="*60)
        self.log_info("성능 측정 요약")
        self.log_info("="*60)
        
        # 개별 작업 통계
        self.log_info("\n📈 작업별 통계:")
        for operation, times in self.measurements.items():
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            total_time = sum(times)
            
            self.log_info(f"\n  {operation}:")
            self.log_info(f"    - 실행 횟수: {len(times)}회")
            self.log_info(f"    - 평균 시간: {avg_time:.3f}초")
            self.log_info(f"    - 최소 시간: {min_time:.3f}초")
            self.log_info(f"    - 최대 시간: {max_time:.3f}초")
            self.log_info(f"    - 총 시간: {total_time:.3f}초")
        
        # 비교 데이터
        if self.comparison_data:
            self.log_info("\n🔄 Before/After 비교:")
            for operation, data in self.comparison_data.items():
                self.log_info(f"\n  {operation}:")
                self.log_info(f"    - 기존: {data['old']:.3f}초")
                self.log_info(f"    - 최적화: {data['new']:.3f}초")
                self.log_info(f"    - 속도 향상: {data['speedup']:.1f}배")
                self.log_info(f"    - 개선율: {data['improvement']:.1f}%")
        
        # 전체 세션 시간
        self.log_info(f"\n⏱️  전체 세션 시간: {session_elapsed:.2f}초")
        self.log_info(f"📁 로그 파일: {self.log_file.absolute()}")
        self.log_info("\n" + "="*60)
    
    def save_json_report(self, output_file: str = None):
        """JSON 형식 리포트 저장"""
        if output_file is None:
            output_file = self.log_file.with_suffix('.json')
        
        report = {
            'session_start': datetime.fromtimestamp(self.session_start).isoformat(),
            'session_duration': time.time() - self.session_start,
            'measurements': {
                operation: {
                    'count': len(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'total': sum(times),
                    'values': times
                }
                for operation, times in self.measurements.items()
            },
            'comparisons': self.comparison_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log_info(f"\n✓ JSON 리포트 저장: {output_file}")


class PerformanceComparator:
    """
    최적화 전후 성능 비교 유틸리티
    """
    
    @staticmethod
    def compare_file_loading(
        old_load_func: Callable,
        new_load_func: Callable,
        file_list: List[str],
        logger: PerformanceLogger
    ):
        """
        파일 로딩 함수 비교
        
        Args:
            old_load_func: 기존 로딩 함수
            new_load_func: 최적화된 로딩 함수
            file_list: 테스트 파일 리스트
            logger: 성능 로거
        """
        logger.log_info("\n" + "="*60)
        logger.log_info("파일 로딩 성능 비교")
        logger.log_info("="*60)
        logger.log_info(f"테스트 파일 수: {len(file_list)}개")
        
        # 기존 방식
        start = logger.start_timer("기존 파일 로딩")
        try:
            old_result = old_load_func(file_list)
            old_time = logger.end_timer("기존 파일 로딩", start)
        except Exception as e:
            logger.log_warning(f"기존 방식 실패: {e}")
            old_time = 0
        
        # 최적화 방식
        start = logger.start_timer("최적화 파일 로딩")
        try:
            new_result = new_load_func(file_list)
            new_time = logger.end_timer("최적화 파일 로딩", start)
        except Exception as e:
            logger.log_warning(f"최적화 방식 실패: {e}")
            new_time = 0
        
        # 비교
        if old_time > 0 and new_time > 0:
            logger.compare("파일 로딩", old_time, new_time)
    
    @staticmethod
    def compare_table_rendering(
        old_render_func: Callable,
        new_render_func: Callable,
        data,
        logger: PerformanceLogger
    ):
        """테이블 렌더링 비교"""
        logger.log_info("\n" + "="*60)
        logger.log_info("테이블 렌더링 성능 비교")
        logger.log_info("="*60)
        
        # 기존 방식
        start = logger.start_timer("기존 테이블 렌더링")
        old_result = old_render_func(data)
        old_time = logger.end_timer("기존 테이블 렌더링", start)
        
        # 최적화 방식
        start = logger.start_timer("최적화 테이블 렌더링")
        new_result = new_render_func(data)
        new_time = logger.end_timer("최적화 테이블 렌더링", start)
        
        # 비교
        logger.compare("테이블 렌더링", old_time, new_time)


# ===== 편의 함수 (전역 로거) =====

_global_logger = None


def get_global_logger() -> PerformanceLogger:
    """전역 성능 로거 가져오기"""
    global _global_logger
    if _global_logger is None:
        _global_logger = PerformanceLogger()
    return _global_logger


def measure_time(operation_name: str):
    """
    전역 로거를 사용한 시간 측정 데코레이터
    
    사용법:
        from performance_logger import measure_time
        
        @measure_time("파일 로딩")
        def load_files(files):
            ...
    """
    return get_global_logger().measure_time(operation_name)


def log_performance(message: str):
    """전역 로거에 메시지 출력"""
    get_global_logger().log_info(message)


def generate_final_report():
    """전역 로거의 최종 리포트 생성"""
    logger = get_global_logger()
    logger.generate_summary()
    logger.save_json_report()


# ===== 사용 예시 =====

if __name__ == "__main__":
    # 예시 1: 기본 사용
    logger = PerformanceLogger()
    
    # 데코레이터 사용
    @logger.measure_time("테스트 작업 1")
    def slow_function():
        time.sleep(1.5)
        return "완료"
    
    @logger.measure_time("테스트 작업 2")
    def fast_function():
        time.sleep(0.3)
        return "완료"
    
    # 실행
    slow_function()
    fast_function()
    slow_function()  # 2번 실행
    
    # 수동 측정
    start = logger.start_timer("수동 측정")
    time.sleep(0.5)
    logger.end_timer("수동 측정", start)
    
    # 비교
    logger.compare("예제 최적화", old_time=2.0, new_time=0.3)
    
    # 최종 리포트
    logger.generate_summary()
    logger.save_json_report()
    
    print(f"\n로그 파일 확인: {logger.log_file}")
