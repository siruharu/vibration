"""
1000개 테스트 데이터 생성기
년_월_일-시_분_초_횟수_채널번호.txt 형식
"""
import os
import numpy as np
from datetime import datetime, timedelta


def generate_test_file(filepath,
                       sampling_rate=10240.0,
                       duration=60.0,
                       channel=1,
                       repetition=1,
                       has_b_sensitivity=True):
    """
    테스트용 txt 파일 생성

    Args:
        filepath: 저장 경로
        sampling_rate: 샘플링 레이트 (Hz)
        duration: 녹음 길이 (초)
        channel: 채널 번호
        repetition: 반복 횟수
        has_b_sensitivity: b.Sensitivity 포함 여부
    """

    # 샘플 개수 계산
    n_samples = int(sampling_rate * duration)

    # 파일명에서 시작 시간 추출
    filename = os.path.basename(filepath)
    # 예: 2026-01-04_08-27-02_1_1.txt
    parts = filename.replace('.txt', '').split('_')

    if len(parts) >= 2:
        date_str = parts[0]  # 2026-01-04
        time_str = parts[1]  # 08-27-02
        start_time = f"{date_str} {time_str}"
    else:
        start_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

    # 헤더 생성
    dt = 1.0 / sampling_rate

    lines = []
    lines.append(f"D.Sampling Freq.         : {sampling_rate} Hz")
    lines.append(f"Time Resolution(dt)      : {dt:.8e} s")
    lines.append(f"Starting time            : {start_time}")
    lines.append(f"Record Length            : {int(duration)} s")
    lines.append(f"Rest time                : 60 s")
    lines.append(f"Repetition               : {repetition} from 100000")
    lines.append(f"Channel                  : {channel}")
    lines.append(f"IEPE enable              : 1")

    # b.Sensitivity 추가 (50% 확률)
    if has_b_sensitivity:
        b_sens = np.random.uniform(10.0, 11.0)
        lines.append(f"b.Sensitivity              : {b_sens:.4f} mv/unit")

    sens = 10.0
    lines.append(f"Sensitivity              : {sens} mv/unit")
    lines.append("")  # 빈 줄

    # 데이터 생성 (실제 진동 패턴 시뮬레이션)
    t = np.linspace(0, duration, n_samples)

    # 여러 주파수 성분 합성
    freq1 = 50  # Hz (주요 진동)
    freq2 = 120  # Hz (2차 고조파)
    freq3 = 300  # Hz (고주파 노이즈)

    signal = (
            5.0 * np.sin(2 * np.pi * freq1 * t) +
            2.0 * np.sin(2 * np.pi * freq2 * t) +
            0.5 * np.sin(2 * np.pi * freq3 * t) +
            np.random.normal(0, 0.1, n_samples)  # 노이즈
    )

    # 데이터 추가
    for value in signal:
        lines.append(f"{value:.6f}")

    # 파일 저장
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))

    return filepath


def generate_batch_test_files(output_dir,
                              num_files=1000,
                              start_date="2026-01-01 00-00-00",
                              time_increment_minutes=10):
    """
    대량 테스트 파일 생성

    Args:
        output_dir: 출력 디렉토리
        num_files: 생성할 파일 개수
        start_date: 시작 날짜/시간 (문자열)
        time_increment_minutes: 시간 증가 간격 (분)
    """

    os.makedirs(output_dir, exist_ok=True)

    # 시작 시간 파싱
    start_dt = datetime.strptime(start_date, "%Y-%m-%d %H-%M-%S")

    generated_files = []

    print(f"🚀 {num_files}개 테스트 파일 생성 시작...")
    print(f"📁 출력 디렉토리: {output_dir}")
    print(f"⏰ 시작 시간: {start_date}")
    print(f"⏱️  시간 간격: {time_increment_minutes}분")
    print("-" * 60)

    for i in range(num_files):
        # 현재 시간 계산
        current_dt = start_dt + timedelta(minutes=i * time_increment_minutes)

        # 날짜/시간 포맷
        date_str = current_dt.strftime("%Y-%m-%d")
        time_str = current_dt.strftime("%H-%M-%S")

        # 반복 횟수와 채널 번호 (1~6 순환)
        repetition = (i % 10) + 1
        channel = (i % 6) + 1

        # 파일명 생성
        filename = f"{date_str}_{time_str}_{repetition}_{channel}.txt"
        filepath = os.path.join(output_dir, filename)

        # b.Sensitivity 포함 여부 (70% 확률)
        has_b_sensitivity = np.random.random() < 0.7

        # 파일 생성
        generate_test_file(
            filepath=filepath,
            sampling_rate=10240.0,
            duration=60.0,
            channel=channel,
            repetition=repetition,
            has_b_sensitivity=has_b_sensitivity
        )

        generated_files.append(filepath)

        # 진행 상황 표시
        if (i + 1) % 100 == 0:
            print(f"✓ {i + 1}/{num_files} 파일 생성 완료...")

    print("-" * 60)
    print(f"🎉 총 {len(generated_files)}개 파일 생성 완료!")
    print(f"📊 파일 크기: 약 {os.path.getsize(generated_files[0]) / 1024:.1f} KB/파일")

    # 통계 출력
    total_size = sum(os.path.getsize(f) for f in generated_files)
    print(f"💾 총 크기: {total_size / (1024 ** 2):.1f} MB")

    # 시간 범위 출력
    first_file = os.path.basename(generated_files[0])
    last_file = os.path.basename(generated_files[-1])
    print(f"📅 시간 범위:")
    print(f"   시작: {first_file}")
    print(f"   종료: {last_file}")

    return generated_files


def generate_mixed_duration_files(output_dir, num_files=100):
    """
    다양한 길이의 테스트 파일 생성 (짧은 파일 포함)

    Args:
        output_dir: 출력 디렉토리
        num_files: 생성할 파일 개수
    """

    os.makedirs(output_dir, exist_ok=True)

    # 다양한 길이 (초)
    durations = [0.25, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]

    print(f"🚀 다양한 길이의 {num_files}개 테스트 파일 생성...")

    start_dt = datetime(2026, 1, 1, 0, 0, 0)

    for i in range(num_files):
        # 랜덤하게 길이 선택
        duration = np.random.choice(durations)

        current_dt = start_dt + timedelta(minutes=i * 10)
        date_str = current_dt.strftime("%Y-%m-%d")
        time_str = current_dt.strftime("%H-%M-%S")

        repetition = (i % 10) + 1
        channel = (i % 6) + 1

        filename = f"{date_str}_{time_str}_{repetition}_{channel}.txt"
        filepath = os.path.join(output_dir, filename)

        # b.Sensitivity 포함 여부
        has_b_sensitivity = np.random.random() < 0.7

        generate_test_file(
            filepath=filepath,
            sampling_rate=10240.0,
            duration=duration,
            channel=channel,
            repetition=repetition,
            has_b_sensitivity=has_b_sensitivity
        )

        if (i + 1) % 20 == 0:
            print(f"✓ {i + 1}/{num_files} 파일 생성 완료...")

    print(f"🎉 총 {num_files}개 파일 생성 완료!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='테스트 데이터 생성기')
    parser.add_argument('--output', '-o', default='./test_data',
                        help='출력 디렉토리 (기본값: ./test_data)')
    parser.add_argument('--count', '-n', type=int, default=1000,
                        help='생성할 파일 개수 (기본값: 1000)')
    parser.add_argument('--start', '-s', default='2026-01-01 00-00-00',
                        help='시작 날짜/시간 (형식: YYYY-MM-DD HH-MM-SS)')
    parser.add_argument('--interval', '-i', type=int, default=10,
                        help='시간 간격 (분, 기본값: 10)')
    parser.add_argument('--mixed', action='store_true',
                        help='다양한 길이의 파일 생성 (짧은 파일 포함)')

    args = parser.parse_args()

    if args.mixed:
        generate_mixed_duration_files(args.output, args.count)
    else:
        generate_batch_test_files(
            output_dir=args.output,
            num_files=args.count,
            start_date=args.start,
            time_increment_minutes=args.interval
        )

    print("\n✅ 완료!")