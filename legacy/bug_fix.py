"""
버그 수정 패치
- JSON 저장 오류 수정
- 폰트 경고 해결
"""

import re
from pathlib import Path


def fix_json_save_bug(source_file: str):
    """
    JSON 저장 버그 수정
    
    문제: json.dump(data, f) 대신 json.dump(data, filepath)로 잘못 호출
    해결: 파일 객체 사용하도록 수정
    """
    
    with open(source_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    print("🔧 JSON 저장 버그 수정 중...")
    
    # 패턴 1: json.dump()에 파일 경로를 직접 전달하는 경우
    # 잘못된 코드 예시:
    #   json.dump(data, filepath)
    # 올바른 코드:
    #   with open(filepath, 'w') as f:
    #       json.dump(data, f)
    
    # json_handler 모듈 사용하도록 변경
    pattern1 = r'json\.dump\(([^,]+),\s*([^)]+)\)'
    
    def replace_json_dump(match):
        data = match.group(1).strip()
        file_arg = match.group(2).strip()
        
        # 파일 객체가 아닌 경우 (변수명에 'path' 또는 따옴표 포함)
        if 'path' in file_arg.lower() or '"' in file_arg or "'" in file_arg:
            # json_handler의 save_json 사용
            return f'save_json({data}, {file_arg})'
        else:
            # 파일 객체인 경우 그대로 유지
            return match.group(0)
    
    code = re.sub(pattern1, replace_json_dump, code)
    
    # 백업 생성
    backup_file = Path(source_file).with_suffix('.backup.py')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # 수정된 코드 저장
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"  ✓ 백업 생성: {backup_file}")
    print(f"  ✓ 수정 완료: {source_file}")


def fix_font_warning(source_file: str):
    """
    폰트 경고 해결
    
    문제: Malgun Gothic에 마이너스 기호 없음
    해결: rcParams 설정 추가
    """
    
    with open(source_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    print("🔧 폰트 경고 수정 중...")
    
    # matplotlib 설정 추가
    font_fix_code = """
# ===== 폰트 설정 (마이너스 기호 문제 해결) =====
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 문제 해결
# ================================================
"""
    
    # import matplotlib 다음에 추가
    if 'import matplotlib' in code and 'axes.unicode_minus' not in code:
        code = code.replace(
            'import matplotlib.pyplot as plt',
            'import matplotlib.pyplot as plt' + font_fix_code
        )
        
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"  ✓ 폰트 설정 추가")
    else:
        print(f"  ⚠ 이미 설정되어 있거나 matplotlib import 없음")


def analyze_json_save_errors(source_file: str):
    """
    JSON 저장 관련 코드 분석
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("\n🔍 JSON 저장 코드 분석:")
    print("="*60)
    
    json_calls = []
    for i, line in enumerate(lines, 1):
        if 'json.dump' in line or 'json.save' in line:
            json_calls.append((i, line.strip()))
    
    if json_calls:
        print(f"발견된 JSON 저장 코드: {len(json_calls)}개")
        for line_num, code in json_calls[:10]:  # 처음 10개만 표시
            print(f"  라인 {line_num}: {code}")
    else:
        print("JSON 저장 코드를 찾을 수 없습니다")
    
    print("="*60)


# ===== 간단한 수정 스크립트 =====

def quick_fix_json_handler():
    """
    json_handler 모듈이 제대로 import되었는지 확인하고 수정
    """
    
    fix_code = """
# ===== JSON 저장 수정 (간단 버전) =====
# 기존 코드에서 json.dump() 호출을 찾아서 수정

# 방법 1: json_handler 사용 (권장)
from json_handler import save_json, load_json

# 기존:
# with open(filepath, 'w') as f:
#     json.dump(data, f)

# 수정:
save_json(data, filepath)

# 방법 2: 기존 코드 수정
# 파일 경로를 파일 객체로 변경
with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f)  # filepath 대신 f 전달
"""
    
    print(fix_code)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python bug_fix.py 'cn_3F_trend_optimized.py'")
        sys.exit(1)
    
    source_file = sys.argv[1]
    
    print("="*60)
    print("버그 수정 시작")
    print("="*60)
    
    # 1. 분석
    analyze_json_save_errors(source_file)
    
    # 2. JSON 저장 수정
    # fix_json_save_bug(source_file)
    
    # 3. 폰트 경고 수정
    # fix_font_warning(source_file)
    
    print("\n" + "="*60)
    print("수동 수정 가이드")
    print("="*60)
    quick_fix_json_handler()
