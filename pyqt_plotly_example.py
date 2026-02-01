
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go
import sys

class WaterfallWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Modern Waterfall Viewer')
        self.setGeometry(100, 100, 1200, 800)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Plotly 웹뷰
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Waterfall 생성
        self.create_waterfall()

    def create_waterfall(self):
        # 데이터 (위의 waterfall_data 사용)
        fig = go.Figure(data=[go.Surface(
            z=waterfall_data,
            x=freq,
            y=time,
            colorscale='Jet'
        )])

        fig.update_layout(
            scene=dict(
                xaxis_title='Frequency (Hz)',
                yaxis_title='Time (s)',
                zaxis_title='Amplitude'
            ),
            title='3D Waterfall'
        )

        # HTML로 변환하여 웹뷰에 표시
        html = fig.to_html(include_plotlyjs='cdn')
        self.web_view.setHtml(html)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WaterfallWindow()
    window.show()
    sys.exit(app.exec_())
