"""
프로젝트 저장 및 로드 서비스.

프로젝트 데이터를 JSON 형식으로 저장하고 로드합니다.
Qt 의존성 없음 - 순수 Python 구현.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from vibration.core.domain.models import ProjectData, ProjectFileInfo


class ProjectService:
    """프로젝트 저장/로드를 위한 서비스 레이어."""

    RESULT_SUBDIRS = [
        'results/spectrum',
        'results/trend',
        'results/peak',
    ]

    def save_project(
        self,
        project_data: ProjectData,
        save_location: str,
    ) -> str:
        """
        프로젝트를 JSON 파일로 저장하고 프로젝트 폴더를 생성합니다.

        인자:
            project_data: 저장할 프로젝트 데이터.
            save_location: 프로젝트 폴더를 생성할 상위 디렉토리.

        반환:
            생성된 project.json의 절대 경로.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_name = f"{project_data.name}_{timestamp}"
        project_data.project_folder = folder_name

        project_dir = Path(save_location) / folder_name
        project_dir.mkdir(parents=True, exist_ok=True)

        for subdir in self.RESULT_SUBDIRS:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

        json_path = project_dir / 'project.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data.to_dict(), f, ensure_ascii=False, indent=2)

        return str(json_path)

    def load_project(self, json_path: str) -> Optional[ProjectData]:
        """
        JSON 파일에서 프로젝트 데이터를 로드합니다.

        인자:
            json_path: project.json 파일 경로.

        반환:
            ProjectData 객체 또는 로드 실패 시 None.
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ProjectData.from_dict(data)
        except Exception:
            return None

    def create_project_folders(self, project_dir: str) -> None:
        """프로젝트 결과 저장을 위한 하위 디렉토리를 생성합니다."""
        base = Path(project_dir)
        for subdir in self.RESULT_SUBDIRS:
            (base / subdir).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def build_project_data(
        parent_folder: str,
        description: str,
        grouped_data: List[Dict[str, Any]],
        measurement_type: str = 'Unknown',
    ) -> ProjectData:
        """
        그룹화된 파일 데이터로부터 ProjectData를 빌드합니다.

        인자:
            parent_folder: 데이터 상위 폴더 절대 경로.
            description: 사용자 입력 설명.
            grouped_data: 프레젠터의 그룹화된 파일 목록.
            measurement_type: 측정 유형 (ACC/Pa/Unknown).

        반환:
            저장 준비가 완료된 ProjectData 객체.
        """
        parent_path = Path(parent_folder)
        name = parent_path.name
        now = datetime.now().isoformat(timespec='seconds')

        file_infos: List[ProjectFileInfo] = []
        all_channels = set()
        all_dates = set()
        sampling_rates: List[float] = []

        for group in grouped_data:
            date_str = group.get('date', '')
            time_str = group.get('time', '')
            is_anomaly = group.get('is_anomaly', False)

            if date_str:
                all_dates.add(date_str)

            for filepath in group.get('file_paths', []):
                fp = Path(filepath)
                try:
                    rel = str(fp.relative_to(parent_path))
                except ValueError:
                    rel = fp.name

                channel = group.get('channel', '')
                sr = group.get('sampling_rate', 0.0)
                sensitivity = group.get('sensitivity', '')

                if channel:
                    all_channels.add(channel)
                if sr > 0:
                    sampling_rates.append(sr)

                file_infos.append(ProjectFileInfo(
                    relative_path=rel,
                    date=date_str,
                    time=time_str,
                    channel=channel,
                    sampling_rate=sr,
                    sensitivity=sensitivity,
                    is_anomaly=is_anomaly,
                ))

        common_sr = 0.0
        if sampling_rates:
            from collections import Counter
            sr_counts = Counter(sampling_rates)
            common_sr = sr_counts.most_common(1)[0][0]

        sorted_dates = sorted(all_dates)
        summary = {
            'total_files': len(file_infos),
            'date_range': [sorted_dates[0], sorted_dates[-1]] if sorted_dates else [],
            'channels': sorted(all_channels),
            'common_sampling_rate': common_sr,
        }

        return ProjectData(
            name=name,
            description=description,
            created_at=now,
            parent_folder=str(parent_path),
            measurement_type=measurement_type,
            files=file_infos,
            summary=summary,
        )
