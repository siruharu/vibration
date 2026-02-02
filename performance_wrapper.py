"""
성능 측정 데코레이터 - 모든 주요 함수에 자동 적용
"""
from performance_logger import PerformanceLogger
import functools

# 전역 로거
perf_logger = PerformanceLogger()


def measure_performance(func_name=None):
    """함수 실행 시간을 자동으로 측정하는 데코레이터"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 함수 이름 결정
            name = func_name or func.__name__

            # 시작 시간 기록
            start = perf_logger.start_timer(name)

            try:
                # 원본 함수 실행
                result = func(*args, **kwargs)

                # 종료 시간 기록
                elapsed = perf_logger.end_timer(name, start)
                perf_logger.log_info(f"✓ {name} 완료: {elapsed:.3f}초")

                return result

            except Exception as e:
                # 오류 발생 시에도 시간 기록
                perf_logger.end_timer(name, start)
                perf_logger.log_warning(f"❌ {name} 실패: {e}")
                raise

        return wrapper

    return decorator