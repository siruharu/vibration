#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간편 자동 패처
- cn 3F trend.py를 찾아서 자동으로 최적화
- 백업 자동 생성
- 한 번의 실행으로 완료
"""

import os
import sys
from pathlib import Path


def find_source_file():
    """현재 디렉토리에서 원본 파일 찾기"""
    current_dir = Path.cwd()
    
    # 가능한 파일명들
    candidates = [
        'cn 3F trend.py',
        'cn_3F_trend.py',
        'cn 3f trend.py'
    ]
    
    for filename in candidates:
        filepath = current_dir / filename
        if filepath.exists():
            return str(filepath)
    
    return None


def main():
    print("="*60)
    print("간편 자동 패처")
    print("="*60)
    
    # 원본 파일 찾기
    print("\n1. 원본 파일 찾기...")
    source_file = find_source_file()
    
    if not source_file:
        print("❌ 원본 파일을 찾을 수 없습니다!")
        print("\n다음 중 하나의 파일이 필요합니다:")
        print("  - cn 3F trend.py")
        print("  - cn_3F_trend.py")
        print("  - cn 3f trend.py")
        print("\n현재 디렉토리:", Path.cwd())
        sys.exit(1)
    
    print(f"✓ 원본 파일 발견: {source_file}")
    
    # auto_patcher 모듈 import
    print("\n2. 패처 모듈 로드...")
    try:
        from auto_patcher import CodePatcher
        print("✓ 패처 모듈 로드 완료")
    except ImportError as e:
        print(f"❌ 패처 모듈을 찾을 수 없습니다: {e}")
        print("auto_patcher.py가 같은 디렉토리에 있는지 확인하세요")
        sys.exit(1)
    
    # 패치 실행
    print("\n3. 패치 적용 중...")
    try:
        patcher = CodePatcher(source_file, backup=True)
        patcher.apply_all_patches()
        
        # 출력 파일명 생성
        output_file = Path(source_file).with_stem(
            Path(source_file).stem + '_optimized'
        )
        
        patcher.save_patched_code(str(output_file))
        patcher.generate_diff_report()
        
        print("\n" + "="*60)
        print("✅ 패치 완료!")
        print("="*60)
        print(f"\n생성된 파일: {output_file}")
        print(f"백업 파일: {patcher.backup_file}")
        
        print("\n다음 단계:")
        print(f"1. {output_file} 검토")
        print("2. INTEGRATION_GUIDE.py 참고하여 수동 수정")
        print("3. 테스트 실행")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 패치 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
