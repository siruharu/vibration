"""
자동 패치 스크립트
- cn 3F trend.py를 자동으로 최적화
- UI 코드는 그대로 유지
- 백업 자동 생성
"""

import re
import shutil
from pathlib import Path
from datetime import datetime


class CodePatcher:
    """
    기존 코드 자동 패칭
    """
    
    def __init__(self, source_file: str, backup: bool = True):
        """
        Args:
            source_file: 패치할 파일 경로
            backup: 백업 생성 여부
        """
        self.source_file = Path(source_file)
        self.backup_file = None
        
        if not self.source_file.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없음: {source_file}")
        
        # 백업 생성
        if backup:
            self.create_backup()
        
        # 원본 코드 읽기
        with open(self.source_file, 'r', encoding='utf-8') as f:
            self.original_code = f.read()
        
        self.patched_code = self.original_code
    
    def create_backup(self):
        """백업 파일 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_file = self.source_file.with_suffix(f'.backup_{timestamp}.py')
        shutil.copy(self.source_file, self.backup_file)
        print(f"✓ 백업 생성: {self.backup_file}")
    
    def patch_imports(self):
        """Import 부분 패치"""
        print("📝 Import 섹션 패치 중...")
        
        # 최적화 모듈 import 추가
        optimization_imports = """
# ===== 최적화 모듈 (자동 추가) =====
from file_loader_optimized import FileLoaderOptimized
from json_handler import save_json, load_json, TrendDetailBridge
from table_optimizer import OptimizedTableView, TableWidgetConverter
from visualization_enhanced import WaterfallPlotEnhanced, FFTPlotEnhanced
from platform_config import initialize_platform_support, get_platform_manager
# ====================================
"""
        
        # import 섹션 찾기 (일반적으로 파일 상단)
        import_pattern = r'(import sys\nimport os)'
        
        if re.search(import_pattern, self.patched_code):
            self.patched_code = re.sub(
                import_pattern,
                r'\1\n' + optimization_imports,
                self.patched_code,
                count=1
            )
            print("  ✓ Import 추가 완료")
        else:
            # fallback: 첫 번째 import 문 다음에 추가
            first_import = re.search(r'(^import .+$)', self.patched_code, re.MULTILINE)
            if first_import:
                insert_pos = first_import.end()
                self.patched_code = (
                    self.patched_code[:insert_pos] +
                    '\n' + optimization_imports +
                    self.patched_code[insert_pos:]
                )
                print("  ✓ Import 추가 완료 (fallback)")
    
    def patch_main_function(self):
        """Main 함수 패치 (플랫폼 초기화 추가)"""
        print("📝 Main 함수 패치 중...")
        
        # if __name__ == "__main__": 찾기
        main_pattern = r'(if __name__ == ["\']__main__["\']:)\s*\n'
        
        init_code = """
    # ===== 플랫폼 초기화 (자동 추가) =====
    initialize_platform_support()
    # ====================================
"""
        
        if re.search(main_pattern, self.patched_code):
            self.patched_code = re.sub(
                main_pattern,
                r'\1\n' + init_code + '\n',
                self.patched_code
            )
            print("  ✓ Main 함수 초기화 추가 완료")
    
    def patch_file_loading(self):
        """파일 로딩 함수 패치"""
        print("📝 파일 로딩 함수 패치 중...")
        
        # 순차 로딩 패턴 찾기 (일반적인 for 루프)
        # 패턴: for ... in file_list: ... load ...
        
        # 방법: monkey patching으로 함수 교체
        monkey_patch = """
# ===== 파일 로딩 최적화 (자동 추가) =====
_original_load_files = None
if hasattr(locals().get('self', None), 'load_files'):
    _original_load_files = self.load_files
    
def _optimized_load_files(self):
    '''최적화된 파일 로딩 (병렬 처리)'''
    loader = FileLoaderOptimized(max_workers=6)
    return loader.load_files_parallel(getattr(self, 'selected_files', []))

# 기존 함수 교체 (필요 시)
# self.load_files = lambda: _optimized_load_files(self)
# ==========================================
"""
        # 클래스 정의 끝부분에 추가하는 것이 안전
        # 여기서는 주석으로 제공 (수동 적용 권장)
        
        print("  ⚠ 파일 로딩 패치는 수동 확인 필요 (INTEGRATION_GUIDE.py 참고)")
    
    def patch_json_handling(self):
        """JSON 저장/로드 패치"""
        print("📝 JSON 처리 함수 패치 중...")
        
        # json.dump 패턴 찾기
        json_dump_pattern = r'json\.dump\((.+?),\s*(.+?)\)'
        
        # save_json으로 교체
        def replace_json_dump(match):
            data = match.group(1)
            file = match.group(2)
            return f'save_json({data}, {file})'
        
        # 교체 수행
        original_count = len(re.findall(json_dump_pattern, self.patched_code))
        self.patched_code = re.sub(json_dump_pattern, replace_json_dump, self.patched_code)
        
        # json.load 패턴 찾기
        json_load_pattern = r'json\.load\((.+?)\)'
        
        def replace_json_load(match):
            file = match.group(1)
            return f'load_json({file})'
        
        load_count = len(re.findall(json_load_pattern, self.patched_code))
        self.patched_code = re.sub(json_load_pattern, replace_json_load, self.patched_code)
        
        print(f"  ✓ json.dump 교체: {original_count}개")
        print(f"  ✓ json.load 교체: {load_count}개")
    
    def patch_table_creation(self):
        """테이블 생성 패치"""
        print("📝 테이블 생성 패치 중...")
        
        # QTableWidget 생성 패턴
        table_pattern = r'QTableWidget\((\d+),\s*(\d+)\)'
        
        # 주석으로 OptimizedTableView 사용 권장 추가
        comment = """
# ===== 테이블 최적화 힌트 (자동 추가) =====
# 성능 향상을 위해 OptimizedTableView 사용 권장:
# self.table = OptimizedTableView(data_array, headers)
# ==========================================
"""
        
        # 첫 번째 QTableWidget 앞에 주석 추가
        if re.search(table_pattern, self.patched_code):
            first_table = re.search(table_pattern, self.patched_code)
            insert_pos = first_table.start()
            self.patched_code = (
                self.patched_code[:insert_pos] +
                comment + '\n' +
                self.patched_code[insert_pos:]
            )
            print("  ✓ 테이블 최적화 힌트 추가 완료")
    
    def apply_all_patches(self):
        """모든 패치 적용"""
        print("\n" + "="*60)
        print("자동 패치 시작")
        print("="*60 + "\n")
        
        self.patch_imports()
        self.patch_main_function()
        self.patch_json_handling()
        self.patch_table_creation()
        
        print("\n" + "="*60)
        print("패치 완료")
        print("="*60)
    
    def save_patched_code(self, output_file: str = None):
        """패치된 코드 저장"""
        if output_file is None:
            # 원본 파일에 _optimized 추가
            output_file = self.source_file.with_stem(
                self.source_file.stem + '_optimized'
            )
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.patched_code)
        
        print(f"\n✓ 패치된 코드 저장: {output_file}")
        return output_file
    
    def generate_diff_report(self):
        """변경 사항 리포트 생성"""
        print("\n" + "="*60)
        print("변경 사항 요약")
        print("="*60)
        
        # 라인 수 비교
        original_lines = self.original_code.count('\n')
        patched_lines = self.patched_code.count('\n')
        
        print(f"원본 라인 수: {original_lines}")
        print(f"패치 후 라인 수: {patched_lines}")
        print(f"추가된 라인: {patched_lines - original_lines}")
        
        # Import 개수
        original_imports = len(re.findall(r'^import |^from .+ import', self.original_code, re.MULTILINE))
        patched_imports = len(re.findall(r'^import |^from .+ import', self.patched_code, re.MULTILINE))
        
        print(f"\nImport 문:")
        print(f"  원본: {original_imports}개")
        print(f"  패치 후: {patched_imports}개")
        print(f"  추가: {patched_imports - original_imports}개")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='코드 자동 최적화 패처')
    parser.add_argument('source_file', help='패치할 파일 경로')
    parser.add_argument('--output', '-o', help='출력 파일 경로', default=None)
    parser.add_argument('--no-backup', action='store_true', help='백업 생성 안 함')
    
    args = parser.parse_args()
    
    # 패처 생성
    patcher = CodePatcher(args.source_file, backup=not args.no_backup)
    
    # 패치 적용
    patcher.apply_all_patches()
    
    # 저장
    output_file = patcher.save_patched_code(args.output)
    
    # 리포트
    patcher.generate_diff_report()
    
    print("\n" + "="*60)
    print("다음 단계:")
    print("="*60)
    print(f"1. {output_file} 파일 검토")
    print("2. INTEGRATION_GUIDE.py 참고하여 수동 수정 부분 확인")
    print("3. 테스트 실행")
    print("4. 성능 측정")
    print("="*60)


if __name__ == "__main__":
    import sys
    
    # 인자가 있으면 실제 실행, 없으면 도움말
    if len(sys.argv) > 1:
        main()
    else:
        # 도움말 출력
        print(__doc__)
        print("\n사용법:")
        print("  python auto_patcher.py 'cn 3F trend.py'")
        print("  python auto_patcher.py 'cn 3F trend.py' --output 'cn_3F_trend_v2.py'")
        print("  python auto_patcher.py 'cn 3F trend.py' --no-backup")
        print("\n예시:")
        print("  python auto_patcher.py 'cn 3F trend.py'")
        sys.exit(0)
