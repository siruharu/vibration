"""
================================================================
Level 4 최적화: UI 렌더링 최적화 + 병렬 저장
================================================================
- 레전드 최적화 (1000개 → 샘플링)
- draw_idle() + flush_events() (비동기 렌더링)
- 트렌드 데이터 병렬 저장 (순차 → 병렬)
- 라인 수 제한 옵션

예상 성능:
- 렌더링 후 UI 응답: 즉각 (기존: 수십 초)
- 트렌드 저장: 5초 (기존: 30-60초)
================================================================
"""

import os
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from PyQt5.QtWidgets import QApplication


# ========================================
# 1. 레전드 최적화 렌더러
# ========================================
class OptimizedRenderer:
    """UI 락 방지 렌더링"""

    @staticmethod
    def render_with_limited_legend(ax, waveax, results, colors, max_legend_items=10):
        """
        레전드 항목 제한 + 비동기 렌더링
        """
        # 기존 렌더링 로직은 그대로
        # ...

        # ⭐ 레전드 샘플링
        handles, labels = ax.get_legend_handles_labels()
        if len(handles) > max_legend_items:
            step = len(handles) // max_legend_items
            handles = handles[::step]
            labels = labels[::step]

        ax.legend(handles, labels, fontsize=7,
                  loc='upper left', bbox_to_anchor=(1, 1))

        # waveform도 동일
        handles_w, labels_w = waveax.get_legend_handles_labels()
        if len(handles_w) > max_legend_items:
            step = len(handles_w) // max_legend_items
            handles_w = handles_w[::step]
            labels_w = labels_w[::step]

        waveax.legend(handles_w, labels_w, fontsize=7,
                      loc='upper left', bbox_to_anchor=(1, 1))

    @staticmethod
    def async_draw(canvas, wavecanvas):
        """
        비동기 렌더링 (UI 블록 방지)
        """
        # 백그라운드 렌더링 예약
        canvas.draw_idle()
        wavecanvas.draw_idle()

        # UI 이벤트 처리
        QApplication.processEvents()

        # 렌더링 완료 대기
        canvas.flush_events()
        wavecanvas.flush_events()


# ========================================
# 2. 병렬 트렌드 데이터 저장
# ========================================
class ParallelTrendSaver:
    """트렌드 데이터 병렬 저장"""

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers

    def save_single_trend(self, save_task: Dict[str, Any]) -> bool:
        """단일 트렌드 데이터 저장"""
        try:
            file_name = save_task['file_name']
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            directory_path = save_task['directory_path']

            save_folder = os.path.join(directory_path, 'trend_data')
            os.makedirs(save_folder, exist_ok=True)

            save_path = os.path.join(save_folder, f"{base_name}.json")

            trend_data = {
                "rms_value": save_task['rms_value'],
                "delta_f": save_task['delta_f'],
                "window": save_task['window_type'],
                "overlap": save_task['overlap'],
                "band_min": save_task['band_min'],
                "band_max": save_task['band_max'],
                "sampling_rate": save_task['sampling_rate'],
                "start_time": str(save_task['start_time']),
                "dt": save_task['dt'],
                "filename": file_name,
                "duration": save_task['duration'],
                "rest_time": save_task['rest_time'],
                "repetition": save_task['repetition'],
                "iepe": save_task['iepe'],
                "sensitivity": save_task['sensitivity'],
                "b_sensitivity": save_task['b_sensitivity'],
                "channel_num": save_task['channel_num'],
                "view_type": save_task['view_type'],
            }

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(trend_data, f, indent=4, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"⚠️ 저장 실패: {save_task.get('file_name', 'unknown')}, {e}")
            return False

    def save_batch(self, save_tasks: List[Dict[str, Any]]) -> Dict[str, int]:
        """병렬 배치 저장"""
        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.save_single_trend, task)
                       for task in save_tasks]

            for future in futures:
                if future.result():
                    success_count += 1
                else:
                    fail_count += 1

        return {
            'success': success_count,
            'failed': fail_count,
            'total': len(save_tasks)
        }


# ========================================
# 3. 라인 수 제한 필터
# ========================================
class LineCountLimiter:
    """표시 라인 수 제한"""

    @staticmethod
    def limit_results(results, max_lines: int = 100):
        """
        결과 리스트를 max_lines 개수로 샘플링

        Args:
            results: 파일 처리 결과 리스트
            max_lines: 최대 표시 라인 수

        Returns:
            샘플링된 결과 리스트
        """
        if len(results) <= max_lines:
            return results

        step = len(results) // max_lines
        return results[::step]


# ========================================
# 사용 예시
# ========================================
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    print("✅ Level 4 렌더링 최적화 모듈 로드 완료")
    saver = ParallelTrendSaver(max_workers=6)
    print(f"   - 병렬 저장 워커: {saver.max_workers}")
    print("   - 레전드 샘플링 활성화")
    print("   - 비동기 렌더링 활성화")