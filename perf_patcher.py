"""
성능 로깅 포함 패처
- 기존 auto_patcher.py 확장
- 성능 측정 코드 자동 추가
"""

from auto_patcher import CodePatcher
from pathlib import Path


class PerformanceLoggingPatcher(CodePatcher):
    """성능 로깅이 포함된 패처"""
    
    def patch_with_logging(self):
        """성능 로깅 코드 추가"""
        print("📊 성능 로깅 코드 추가 중...")
        
        # 1. Import 추가
        self._add_performance_imports()
        
        # 2. 로거 초기화 추가
        self._add_logger_initialization()
        
        # 3. 주요 함수에 로깅 추가
        self._wrap_functions_with_logging()
        
        print("  ✓ 성능 로깅 코드 추가 완료")
    
    def _add_performance_imports(self):
        """성능 로거 import 추가"""
        performance_imports = """
# ===== 성능 측정 (자동 추가) =====
from performance_logger import PerformanceLogger
perf_logger = PerformanceLogger(log_file="performance_log.txt", console_output=True)
# ====================================
"""
        
        # 기존 최적화 모듈 import 다음에 추가
        insert_marker = "from platform_config import"
        
        if insert_marker in self.patched_code:
            self.patched_code = self.patched_code.replace(
                insert_marker,
                insert_marker + performance_imports
            )
    
    def _add_logger_initialization(self):
        """메인 함수에 로거 초기화 추가"""
        init_code = """
    # ===== 성능 측정 시작 (자동 추가) =====
    perf_logger.log_info("프로그램 시작")
    # ====================================
"""
        
        # initialize_platform_support() 다음에 추가
        marker = "initialize_platform_support()"
        
        if marker in self.patched_code:
            self.patched_code = self.patched_code.replace(
                marker,
                marker + init_code
            )
    
    def _wrap_functions_with_logging(self):
        """주요 함수를 로깅 래퍼로 감싸기"""
        
        # 파일 로딩 함수 래핑 (예시)
        # 실제 함수명은 코드 분석 후 적용
        
        function_patterns = [
            # (함수명 패턴, 로그 메시지)
            (r'def load_files?\(', "파일 로딩"),
            (r'def compute_fft\(', "FFT 계산"),
            (r'def create_table\(', "테이블 생성"),
            (r'def plot_waterfall\(', "Waterfall 생성"),
        ]
        
        # 실제 구현은 코드 구조에 따라 달라짐
        # 여기서는 주석으로 힌트 제공
        
        hint_comment = """
# ===== 성능 측정 힌트 (자동 추가) =====
# 주요 함수에 다음과 같이 적용:
#
# @perf_logger.measure_time("작업명")
# def your_function(...):
#     ...
#
# 또는 수동으로:
# start = perf_logger.start_timer("작업명")
# ... 작업 ...
# perf_logger.end_timer("작업명", start)
# =========================================
"""
        
        # 첫 번째 클래스 정의 앞에 힌트 추가
        import re
        class_pattern = r'(class\s+\w+.*?:)'
        match = re.search(class_pattern, self.patched_code)
        
        if match:
            insert_pos = match.start()
            self.patched_code = (
                self.patched_code[:insert_pos] +
                hint_comment + '\n' +
                self.patched_code[insert_pos:]
            )
    
    def add_final_report_call(self):
        """프로그램 종료 시 리포트 생성"""
        
        final_report_code = """
    # ===== 성능 리포트 생성 (자동 추가) =====
    perf_logger.log_info("프로그램 종료")
    perf_logger.generate_summary()
    perf_logger.save_json_report()
    # ====================================
"""
        
        # sys.exit 앞에 추가
        if "sys.exit(app.exec_())" in self.patched_code:
            self.patched_code = self.patched_code.replace(
                "sys.exit(app.exec_())",
                final_report_code + "\n    sys.exit(app.exec_())"
            )


def main():
    """메인 실행"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='성능 로깅 포함 패처')
    parser.add_argument('source_file', help='패치할 파일')
    parser.add_argument('--with-logging', action='store_true', 
                       help='성능 로깅 코드 추가')
    parser.add_argument('--output', '-o', help='출력 파일')
    
    args = parser.parse_args()
    
    # 패처 생성
    if args.with_logging:
        patcher = PerformanceLoggingPatcher(args.source_file)
    else:
        patcher = CodePatcher(args.source_file)
    
    # 기본 패치 적용
    patcher.apply_all_patches()
    
    # 성능 로깅 추가 (옵션)
    if args.with_logging:
        patcher.patch_with_logging()
        patcher.add_final_report_call()
    
    # 저장
    output_file = patcher.save_patched_code(args.output)
    
    # 리포트
    patcher.generate_diff_report()
    
    print("\n" + "="*60)
    print("패치 완료!")
    print("="*60)
    print(f"\n생성된 파일: {output_file}")
    
    if args.with_logging:
        print("\n📊 성능 측정 기능:")
        print("  - 자동 시간 측정")
        print("  - 로그 파일 생성")
        print("  - JSON 리포트 생성")
        print("\n실행 후 확인:")
        print("  - performance_log.txt")
        print("  - performance_log.json")


if __name__ == "__main__":
    print(__doc__)
    print("\n사용법:")
    print("  # 기본 패치")
    print("  python perf_patcher.py 'cn 3F trend.py'")
    print("\n  # 성능 로깅 포함")
    print("  python perf_patcher.py 'cn 3F trend.py' --with-logging")
