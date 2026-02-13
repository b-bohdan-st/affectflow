import sys
import os
import pygame
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)

ALARM_FILE = resource_path("alarm.wav")
ICON_FILE = resource_path("icon.png")

pygame.mixer.init()

class LockScreen(QWidget):
    def __init__(self, screen_geometry, pause_callback):
        super().__init__()
        self.setGeometry(screen_geometry)
        self.pause_callback = pause_callback
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(85, 85, 85, 220))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_title = QLabel("Break in progress.")
        label_title.setFont(QFont("Segoe UI", 24))
        label_title.setStyleSheet("color: white;")
        layout.addWidget(label_title)
        label_pause = QLabel("Click here to pause and unlock")
        label_pause.setFont(QFont("Segoe UI", 14))
        label_pause.setStyleSheet("color: #bbb;")
        layout.addWidget(label_pause)
        self.setLayout(layout)
        label_pause.mousePressEvent = self.mouse_pause

    def mouse_pause(self, event):
        self.pause_callback()

class BreakWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Break Timer")
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        if os.path.exists(ICON_FILE):
            self.setWindowIcon(QIcon(ICON_FILE))
        self.setStyleSheet("background-color: #1f1f1f; color: #eee;")
        self.timer_duration = 0
        self.remaining = 0
        self.is_paused = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.lock_screens = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.label_main = QLabel("Time for a break!")
        self.label_main.setFont(QFont("Segoe UI", 18))
        self.label_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_main)
        
        self.btn_container = QWidget()
        self.btn_layout = QHBoxLayout(self.btn_container)
        self.btn_15 = QPushButton("15 min")
        self.btn_30 = QPushButton("30 min")
        for b in [self.btn_15, self.btn_30]:
            b.setStyleSheet("background-color: #6200ee; color: white; padding: 10px;")
            self.btn_layout.addWidget(b)
        self.btn_15.clicked.connect(lambda: self.set_dur(15))
        self.btn_30.clicked.connect(lambda: self.set_dur(30))
        layout.addWidget(self.btn_container)

        self.lock_checkbox = QCheckBox("Lock screens")
        layout.addWidget(self.lock_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_btn = QPushButton("Start Break")
        self.main_btn.setStyleSheet("background-color: #ff5733; color: white; padding: 12px; font-weight: bold;")
        self.main_btn.clicked.connect(self.handle_main_button)
        layout.addWidget(self.main_btn)

        self.stop_btn = QPushButton("Stop Break")
        self.stop_btn.setStyleSheet("background-color: #d32f2f; color: white; padding: 10px;")
        self.stop_btn.clicked.connect(self.reset_timer)
        self.stop_btn.hide()
        layout.addWidget(self.stop_btn)

        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Segoe UI", 24))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        self.setLayout(layout)

    def set_dur(self, m):
        if not self.timer.isActive() and not self.is_paused:
            self.timer_duration = m * 60
            self.remaining = self.timer_duration
            self.timer_label.setText(f"{m:02d}:00")

    def handle_main_button(self):
        if self.remaining <= 0: return
        if not self.timer.isActive() and not self.is_paused:
            self.start_br()
        elif self.timer.isActive():
            self.pause_br()
        elif self.is_paused:
            self.continue_br()

    def start_br(self):
        self.main_btn.setText("Pause break")
        self.btn_container.setEnabled(False)
        self.lock_checkbox.setEnabled(False)
        if self.lock_checkbox.isChecked():
            self.show_locks()
        self.timer.start(1000)

    def pause_br(self):
        self.timer.stop()
        self.is_paused = True
        self.main_btn.setText("Continue break")
        self.stop_btn.show()
        self.close_locks()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def continue_br(self):
        self.is_paused = False
        self.main_btn.setText("Pause break")
        self.stop_btn.hide()
        if self.lock_checkbox.isChecked():
            self.show_locks()
        self.timer.start(1000)

    def reset_timer(self):
        self.timer.stop()
        self.remaining = 0
        self.is_paused = False
        self.timer_label.setText("00:00")
        self.main_btn.setText("Start Break")
        self.stop_btn.hide()
        self.btn_container.setEnabled(True)
        self.lock_checkbox.setEnabled(True)
        self.close_locks()

    def update_timer(self):
        if self.remaining <= 0:
            self.timer.stop()
            self.finish_br()
        else:
            self.remaining -= 1
            m, s = divmod(self.remaining, 60)
            self.timer_label.setText(f"{m:02d}:{s:02d}")

    def show_locks(self):
        self.close_locks()
        for s in QApplication.screens():
            ls = LockScreen(s.geometry(), self.pause_br)
            ls.show()
            self.lock_screens.append(ls)

    def close_locks(self):
        for ls in self.lock_screens:
            ls.close()
        self.lock_screens.clear()

    def finish_br(self):
        self.close_locks()
        if os.path.exists(ALARM_FILE):
            try:
                pygame.mixer.music.load(ALARM_FILE)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    QApplication.processEvents()
            except: pass
        print("break_ended")
        sys.stdout.flush()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = BreakWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    sys.exit(app.exec())