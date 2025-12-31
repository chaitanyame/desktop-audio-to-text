import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint

class CaptionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.oldPos = None
        self.initUI()

    def initUI(self):
        # Window setup
        self.setWindowTitle('Live Captions')
        self.setGeometry(100, 100, 800, 250)
        
        # Remove frame and keep on top
        # Removed Qt.WindowType.Tool so it appears in taskbar (needed for minimize)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # REMOVED: WA_TransparentForMouseEvents so we can click buttons
        # self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Custom Title Bar ---
        self.title_bar = QWidget()
        self.title_bar.setStyleSheet("background-color: rgba(30, 30, 30, 200); border-top-left-radius: 10px; border-top-right-radius: 10px;")
        self.title_bar.setFixedHeight(40)
        
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setContentsMargins(10, 0, 10, 0)
        
        self.title_label = QLabel("Live Captions (Drag to move)")
        self.title_label.setStyleSheet("color: #ddd; font-size: 12px;")
        
        self.btn_minimize = QPushButton("_")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_minimize.setStyleSheet("""
            QPushButton { color: white; background-color: transparent; font-weight: bold; }
            QPushButton:hover { background-color: #555; }
        """)
        
        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.clicked.connect(self.close_app)
        self.btn_close.setStyleSheet("""
            QPushButton { color: white; background-color: transparent; font-weight: bold; }
            QPushButton:hover { background-color: #cc0000; }
        """)

        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()
        self.title_layout.addWidget(self.btn_minimize)
        self.title_layout.addWidget(self.btn_close)
        
        self.layout.addWidget(self.title_bar)
        # ------------------------

        # Label for text
        self.label = QLabel("Waiting for audio...", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-family: Arial;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 150);
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                padding: 10px;
            }
        """)
        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)
        self.layout.addStretch()

        # Position at bottom of screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            (screen.width() - 800) // 2,
            screen.height() - 350,
            800,
            250
        )

    def update_text(self, text):
        self.label.setText(text)

    def close_app(self):
        # Force exit
        import sys
        sys.exit(0)

    # --- Dragging Logic ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CaptionWindow()
    window.show()
    sys.exit(app.exec())
