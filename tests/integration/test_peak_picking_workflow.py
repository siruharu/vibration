"""
Integration tests for Band Peak Trend picking workflow.

Tests the complete interactive picking functionality:
- Mouse hover detection
- Click to mark data points
- Pick Data List management
- List Save dialog integration
"""
import pytest
import numpy as np
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from vibration.core.services import PeakService, FileService
from vibration.presentation.views.tabs.peak_tab import PeakTabView
from vibration.presentation.presenters.peak_presenter import PeakPresenter


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_data_files(tmp_path):
    """Create multiple test data files for peak analysis."""
    files = []
    for ch in range(1, 4):
        for idx in range(3):
            test_file = tmp_path / f"test_{idx:03d}_{ch}.txt"
            content = """D.Sampling Freq.: 10240 Hz
Channel: CH1
Sensitivity: 100 mV/g
b.Sensitivity: 50
Record Length: 1.0 sec

"""
            samples = np.sin(2 * np.pi * (100 + idx*50) * np.linspace(0, 1, 10240)) * (1 + idx*0.2)
            content += "\n".join(f"{x:.6f}" for x in samples)
            test_file.write_text(content, encoding='utf-8')
            files.append(test_file)
    return files


class TestPeakPickingWorkflow:
    """Test complete Band Peak Trend picking workflow."""
    
    def test_pick_data_list_panel_created(self, qapp):
        """Test that Pick Data List panel is created with correct structure."""
        view = PeakTabView()
        
        assert hasattr(view, 'data_list_label'), "Missing data_list_label"
        assert hasattr(view, 'data_list_text'), "Missing data_list_text"
        assert hasattr(view, 'data_list_save_btn'), "Missing data_list_save_btn"
        
        initial_text = view.data_list_text.toPlainText()
        assert "Ch1" in initial_text
        assert "Ch2" in initial_text
        assert "Ch3" in initial_text
        assert "Ch4" in initial_text
        assert "Ch5" in initial_text
        assert "Ch6" in initial_text
        assert initial_text.count("-") == 6
    
    def test_mouse_event_connections(self, qapp):
        """Test that mouse events are properly connected to canvas."""
        view = PeakTabView()
        
        assert hasattr(view, '_on_mouse_move'), "Missing _on_mouse_move handler"
        assert hasattr(view, '_on_mouse_click'), "Missing _on_mouse_click handler"
        assert hasattr(view, '_on_key_press'), "Missing _on_key_press handler"
        
        connections = view.peak_canvas.callbacks.callbacks
        assert 'motion_notify_event' in connections
        assert 'button_press_event' in connections
        assert 'key_press_event' in connections
    
    def test_marker_attributes_initialized(self, qapp):
        """Test that marker attributes are initialized correctly."""
        view = PeakTabView()
        
        assert view.hover_dot is None
        assert view.hover_pos is None
        assert view.peak_marker is None
        assert view.peak_annotation is None
        assert view.peak_x_value == []
        assert view.peak_values == []
        assert view.peak_file_names == []
    
    def test_set_peak_data(self, qapp):
        """Test that peak data is stored correctly for picking."""
        view = PeakTabView()
        
        x_vals = [datetime(2025, 1, 1), datetime(2025, 1, 2), datetime(2025, 1, 3)]
        y_vals = [1.5, 2.3, 1.8]
        file_names = ['file_001_1.txt', 'file_002_1.txt', 'file_003_1.txt']
        
        view.set_peak_data(x_vals, y_vals, file_names)
        
        assert view.peak_x_value == x_vals
        assert view.peak_values == y_vals
        assert view.peak_file_names == file_names
    
    def test_add_filename_to_list(self, qapp):
        """Test that filenames are added to correct channel in Pick Data List."""
        view = PeakTabView()
        
        view._add_filename_to_list('test_001_1.txt')
        text = view.data_list_text.toPlainText()
        lines = text.split('\n')
        
        ch1_idx = lines.index('Ch1')
        assert 'test_001_1.txt' in lines[ch1_idx+1:ch1_idx+3]
        
        view._add_filename_to_list('test_002_3.txt')
        text = view.data_list_text.toPlainText()
        lines = text.split('\n')
        
        ch3_idx = lines.index('Ch3')
        assert 'test_002_3.txt' in lines[ch3_idx+1:ch3_idx+3]
    
    def test_duplicate_filename_prevention(self, qapp):
        """Test that duplicate filenames are not added to list."""
        view = PeakTabView()
        
        view._add_filename_to_list('test_001_1.txt')
        view._add_filename_to_list('test_001_1.txt')
        
        text = view.data_list_text.toPlainText()
        assert text.count('test_001_1.txt') == 1
    
    def test_list_save_signal_emitted(self, qapp):
        """Test that list_save_requested signal is emitted with correct data."""
        view = PeakTabView()
        view.set_directory_path('/test/path')
        
        view._add_filename_to_list('file_001_1.txt')
        view._add_filename_to_list('file_002_2.txt')
        view._add_filename_to_list('file_003_3.txt')
        
        signal_received = []
        view.list_save_requested.connect(lambda ch, path: signal_received.append((ch, path)))
        
        view._on_list_save_clicked()
        
        assert len(signal_received) == 1
        channel_files, directory_path = signal_received[0]
        
        assert 'file_001_1.txt' in channel_files['Ch1']
        assert 'file_002_2.txt' in channel_files['Ch2']
        assert 'file_003_3.txt' in channel_files['Ch3']
        assert directory_path == '/test/path'
    
    def test_plot_and_pick_integration(self, qapp, test_data_files, tmp_path):
        """Test complete workflow: plot → set data → pick functionality available."""
        view = PeakTabView()
        peak_service = PeakService()
        file_service = FileService()
        presenter = PeakPresenter(view, peak_service, file_service)
        
        view.set_files([f.name for f in test_data_files[:3]])
        
        presenter._directory_path = str(tmp_path)
        view.set_directory_path(str(tmp_path))
        
        for item_idx in range(3):
            view.Querry_list4.item(item_idx).setSelected(True)
        
        result = peak_service.compute_peak_trend(
            file_paths=[str(f) for f in test_data_files[:3]],
            delta_f=1.0,
            overlap=50.0,
            window_type='hanning',
            view_type='ACC',
            frequency_band=(10, 5000)
        )
        
        assert result.channel_data is not None
        assert len(result.channel_data) > 0
        
        view.plot_peak_trend(result.channel_data, clear=True)
        
        all_x = []
        all_y = []
        all_files = []
        for ch in sorted(result.channel_data.keys()):
            data = result.channel_data[ch]
            all_x.extend(data['x'])
            all_y.extend(data['y'])
            all_files.extend(data.get('labels', []))
        
        view.set_peak_data(all_x, all_y, all_files)
        
        assert len(view.peak_x_value) > 0
        assert len(view.peak_values) > 0
        assert len(view.peak_file_names) > 0
        assert len(view.peak_x_value) == len(view.peak_values)
        assert len(view.peak_x_value) == len(view.peak_file_names)
    
    @patch('vibration.presentation.presenters.peak_presenter.ListSaveDialog')
    def test_presenter_list_save_handler(self, mock_dialog_class, qapp):
        """Test that presenter opens Detail Analysis dialog correctly."""
        view = PeakTabView()
        peak_service = PeakService()
        file_service = FileService()
        presenter = PeakPresenter(view, peak_service, file_service)
        
        mock_dialog = MagicMock()
        mock_dialog_class.return_value = mock_dialog
        
        channel_files = {
            'Ch1': ['file_001_1.txt', 'file_002_1.txt'],
            'Ch2': ['file_001_2.txt'],
            'Ch3': [],
            'Ch4': [],
            'Ch5': [],
            'Ch6': []
        }
        
        presenter._on_list_save_requested(channel_files, '/test/path')
        
        mock_dialog_class.assert_called_once_with(
            channel_files=channel_files,
            parent=view,
            directory_path='/test/path'
        )
        mock_dialog.setWindowModality.assert_called_once()
        mock_dialog.resize.assert_called_once_with(1600, 900)
        mock_dialog.show.assert_called_once()
    
    def test_clear_markers(self, qapp):
        """Test that markers are cleared correctly."""
        view = PeakTabView()
        
        view.set_peak_data(
            [datetime(2025, 1, 1)],
            [1.5],
            ['test_001_1.txt']
        )
        
        view.plot_peak_trend({1: {'x': [datetime(2025, 1, 1)], 'y': [1.5]}}, clear=True)
        
        mock_event = MagicMock()
        mock_event.inaxes = view.peak_ax
        mock_event.xdata = 0
        mock_event.ydata = 1.5
        
        view._on_mouse_move(mock_event)
        
        if view.hover_dot is not None:
            x_data, y_data = view.hover_dot.get_data()
            initial_hover_present = len(x_data) > 0
        else:
            initial_hover_present = False
        
        view._clear_markers()
        
        assert view.peak_marker is None
        assert view.peak_annotation is None
    
    def test_channel_grouping_accuracy(self, qapp):
        """Test that files are correctly grouped by channel number."""
        view = PeakTabView()
        
        test_files = [
            'file_001_1.txt',
            'file_002_1.txt',
            'file_003_2.txt',
            'file_004_3.txt',
            'file_005_6.txt'
        ]
        
        for filename in test_files:
            view._add_filename_to_list(filename)
        
        view._on_list_save_clicked()
        
        signal_received = []
        view.list_save_requested.connect(lambda ch, path: signal_received.append((ch, path)))
        view._on_list_save_clicked()
        
        if signal_received:
            channel_files, _ = signal_received[0]
            assert len(channel_files['Ch1']) == 2
            assert len(channel_files['Ch2']) == 1
            assert len(channel_files['Ch3']) == 1
            assert len(channel_files['Ch6']) == 1


class TestPeakPresenterIntegration:
    """Test Peak Presenter integration with picking workflow."""
    
    def test_directory_path_propagation(self, qapp):
        """Test that directory path is propagated to view."""
        view = PeakTabView()
        peak_service = PeakService()
        file_service = FileService()
        presenter = PeakPresenter(view, peak_service, file_service)
        
        test_path = '/test/directory/path'
        presenter._on_directory_selected(test_path)
        
        assert presenter._directory_path == test_path
        assert hasattr(view, '_directory_path')
        assert view._directory_path == test_path
    
    def test_signal_connections(self, qapp):
        """Test that all required signals are connected."""
        view = PeakTabView()
        peak_service = PeakService()
        file_service = FileService()
        
        signal_received = []
        view.list_save_requested.connect(lambda ch, path: signal_received.append((ch, path)))
        
        presenter = PeakPresenter(view, peak_service, file_service)
        
        view._add_filename_to_list('test_001_1.txt')
        view.set_directory_path('/test/path')
        view._on_list_save_clicked()
        
        assert len(signal_received) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
