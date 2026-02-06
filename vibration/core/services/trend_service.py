"""
Trend analysis service.

Wraps TrendParallelProcessor for batch RMS trend computation.
NO Qt dependencies - pure Python/NumPy implementation.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Literal

import numpy as np

from .OPTIMIZATION_PATCH_LEVEL5_TREND import TrendParallelProcessor
from vibration.core.domain.models import TrendResult


ViewType = Literal['ACC', 'VEL', 'DIS']
WindowType = Literal['hanning', 'flattop', 'rectangular']

VIEW_TYPE_MAP = {'ACC': 1, 'VEL': 2, 'DIS': 3}
VIEW_TYPE_REVERSE = {1: 'ACC', 2: 'VEL', 3: 'DIS'}


class TrendService:
    """
    Service layer for trend analysis with batch processing.
    
    Wraps TrendParallelProcessor and provides business logic for:
    - Computing RMS trends across multiple files
    - Aggregating results by channel
    - Extracting timestamps from filenames
    
    Args:
        max_workers: Number of parallel workers (default: CPU count - 1).
    """
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers
        self._processor = TrendParallelProcessor(max_workers=max_workers)
    
    def compute_trend(
        self,
        file_paths: List[str],
        delta_f: float = 1.0,
        overlap: float = 50.0,
        window_type: WindowType = 'hanning',
        view_type: ViewType = 'ACC',
        frequency_band: Optional[Tuple[float, float]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> TrendResult:
        """
        Compute RMS trend across multiple files.
        
        Args:
            file_paths: List of file paths to analyze.
            delta_f: Frequency resolution in Hz.
            overlap: Overlap percentage (not used, for compatibility).
            window_type: Window function ('hanning', 'flattop', 'rectangular').
            view_type: Signal type ('ACC', 'VEL', 'DIS').
            frequency_band: (min_freq, max_freq) band filter.
            progress_callback: Optional callback (current, total) for progress.
            
        Returns:
            TrendResult with aggregated trend data.
        """
        if not file_paths:
            return TrendResult(
                timestamps=[],
                rms_values=np.array([]),
                filenames=[],
                view_type=view_type,
                frequency_band=frequency_band
            )
        
        band_min, band_max = frequency_band if frequency_band else (0.0, 5000.0)
        view_type_int = VIEW_TYPE_MAP.get(view_type.upper(), 1)
        
        raw_results = self._processor.process_batch(
            file_paths=file_paths,
            delta_f=delta_f,
            overlap=overlap,
            window_type=window_type.lower(),
            view_type=view_type_int,
            band_min=band_min,
            band_max=band_max,
            progress_callback=progress_callback
        )
        
        return self._aggregate_results(raw_results, view_type.upper(), frequency_band)
    
    def _aggregate_results(
        self,
        raw_results: List,
        view_type: str,
        frequency_band: Optional[Tuple[float, float]]
    ) -> TrendResult:
        """Aggregate raw processor results into TrendResult."""
        success_results = [r for r in raw_results if r.success]
        
        if not success_results:
            return TrendResult(
                timestamps=[],
                rms_values=np.array([]),
                filenames=[],
                view_type=view_type,
                frequency_band=frequency_band,
                metadata={'total_files': len(raw_results), 'failed_count': len(raw_results)}
            )
        
        filenames = []
        rms_values = []
        peak_values = []
        peak_frequencies = []
        timestamps = []
        channel_data = {}
        
        for result in success_results:
            filenames.append(result.file_name)
            rms_values.append(result.rms_value)
            peak_values.append(result.peak_value)
            peak_frequencies.append(result.peak_freq)
            
            ts = self._extract_timestamp(result.file_name)
            timestamps.append(ts)
            
            channel = self._extract_channel(result.file_name)
            if channel not in channel_data:
                channel_data[channel] = {'x': [], 'y': [], 'labels': []}
            channel_data[channel]['x'].append(ts)
            channel_data[channel]['y'].append(result.rms_value)
            channel_data[channel]['labels'].append(result.file_name)
        
        sampling_rate = success_results[0].sampling_rate if success_results else 0.0
        
        return TrendResult(
            timestamps=timestamps,
            rms_values=np.array(rms_values),
            filenames=filenames,
            view_type=view_type,
            frequency_band=frequency_band,
            channel_data=channel_data,
            peak_values=np.array(peak_values),
            peak_frequencies=np.array(peak_frequencies),
            sampling_rate=sampling_rate,
            metadata={
                'total_files': len(raw_results),
                'success_count': len(success_results),
                'failed_count': len(raw_results) - len(success_results)
            }
        )
    
    def _extract_timestamp(self, filename: str) -> datetime:
        """
        Extract timestamp from filename.
        
        Pattern: YYYYMMDD_HHMMSS or similar.
        Falls back to current time if parsing fails.
        """
        patterns = [
            r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',
            r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',
            r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    return datetime(
                        int(groups[0]), int(groups[1]), int(groups[2]),
                        int(groups[3]), int(groups[4]), int(groups[5])
                    )
                except (ValueError, IndexError):
                    continue
        
        return datetime.now()
    
    def _extract_channel(self, filename: str) -> str:
        """Extract channel identifier from filename (typically last segment before extension)."""
        base = Path(filename).stem
        parts = base.split('_')
        return parts[-1] if parts else '0'
    
    def get_parameters(self) -> dict:
        """Get current processor parameters."""
        return {
            'max_workers': self._processor.max_workers
        }


if __name__ == "__main__":
    print("TrendService Test")
    print("=" * 50)
    
    svc = TrendService(max_workers=2)
    print(f"Max workers: {svc.get_parameters()['max_workers']}")
    
    empty_result = svc.compute_trend([], view_type='ACC')
    assert empty_result.num_files == 0
    print("Empty file list handled correctly")
    
    import sys
    assert 'PyQt5' not in sys.modules, "Qt dependency detected!"
    print("\nNo Qt dependency - OK")
    print("TrendService Test PASSED")
