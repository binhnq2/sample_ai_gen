import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QComboBox, QHBoxLayout, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from .parser import parse_java_methods
from .testgen_flow import TestGenFlow

class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)

    def __init__(self, project_path, file_path, method_sig):
        super().__init__()
        self.project_path = project_path
        self.file_path = file_path
        self.method_sig = method_sig

    def run(self):
        def logger(msg):
            self.log_signal.emit(str(msg))
        flow = TestGenFlow(self.project_path, self.file_path, self.method_sig, log_signal=logger)
        out = flow.run()
        self.result_signal.emit(out)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AIJUnitGen - JUnit Test Generator")
        self.resize(1100, 760)
        layout = QVBoxLayout()

        self.project_label = QLabel("Project Folder: (not selected)")
        self.file_label = QLabel("Service Class File: (not selected)")

        self.btn_select_folder = QPushButton("Select Project Folder")
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.btn_select_file = QPushButton("Select Service Class File")
        self.btn_select_file.clicked.connect(self.select_file)

        self.method_combo = QComboBox()
        self.method_combo.addItem("-- Select Method --")

        self.btn_generate = QPushButton("Generate JUnit Test")
        self.btn_generate.clicked.connect(self.generate_test)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.btn_select_folder)
        top_layout.addWidget(self.btn_select_file)
        top_layout.addWidget(self.method_combo)
        top_layout.addWidget(self.btn_generate)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Logs will appear here...")

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setPlaceholderText("Generated JUnit test will appear here...")

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.log_box)
        splitter.addWidget(self.output_box)
        splitter.setSizes([300, 400])

        layout.addWidget(self.project_label)
        layout.addWidget(self.file_label)
        layout.addLayout(top_layout)
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.project_path = None
        self.file_path = None
        self.worker = None

    def append_log(self, text: str):
        self.log_box.append(f"[LOG] {text}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Java Project Folder")
        if folder:
            self.project_path = folder
            self.project_label.setText(f"Project Folder: {folder}")
            self.append_log(f"Selected project: {folder}")

    def select_file(self):
        if not self.project_path:
            self.append_log("Please select a project folder first.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Service Class File", self.project_path, "Java Files (*.java)")
        if file_path:
            self.file_path = file_path
            self.file_label.setText(f"Service Class File: {os.path.relpath(file_path, self.project_path)}")
            methods = parse_java_methods(file_path)
            self.method_combo.clear()
            self.method_combo.addItem("-- Select Method --")
            for m in methods:
                self.method_combo.addItem(m)
            self.append_log(f"Detected methods: {', '.join([m for m in methods])}")

    def generate_test(self):
        if not self.project_path or not self.file_path or self.method_combo.currentText() == "-- Select Method --":
            self.append_log("Please select project, file and method.")
            return
        method_sig = self.method_combo.currentText()
        self.append_log(f"Starting generation for method {method_sig}")
        self.worker = WorkerThread(self.project_path, self.file_path, method_sig)
        self.worker.log_signal.connect(self.append_log)
        self.worker.result_signal.connect(self.show_result)
        self.worker.start()

    def show_result(self, text: str):
        self.append_log("Received generated output.")
        self.output_box.setPlainText(text)
