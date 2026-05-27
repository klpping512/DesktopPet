"""Upload dialog - select pet photo and configure appearance"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QGroupBox, QFormLayout,
                             QFileDialog, QDialogButtonBox, QMessageBox,
                             QProgressBar)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer
from vision.pet_recognizer import PetAnalyzer


class UploadDialog(QDialog):
    """Dialog for uploading and configuring pet photos"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📷 上传宠物照片")
        self.setFixedSize(450, 500)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.image_path = None
        self.preview_pixmap = None
        self.analysis_result = None
        self._user_changed_model = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Upload area ──
        self._upload_btn = QPushButton("📷 选择照片")
        self._upload_btn.setStyleSheet("""
            QPushButton {
                background: #4a7ae8; color: white; font-weight: bold;
                padding: 12px; border-radius: 8px; font-size: 14px;
            }
            QPushButton:hover { background: #3a6ad8; }
        """)
        self._upload_btn.clicked.connect(self._choose_file)
        layout.addWidget(self._upload_btn)

        # ── Preview ──
        self._preview_label = QLabel("尚未选择照片")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setFixedHeight(200)
        self._preview_label.setStyleSheet(
            "background: #f0f0f5; border-radius: 8px; color: #888; font-size: 13px;"
        )
        layout.addWidget(self._preview_label)

        # ── Analysis result ──
        self._result_group = QGroupBox("识别结果")
        self._result_group.setVisible(False)
        result_layout = QFormLayout(self._result_group)

        self._species_label = QLabel("--")
        result_layout.addRow("物种:", self._species_label)
        self._color_label = QLabel("--")
        result_layout.addRow("颜色:", self._color_label)
        self._pattern_label = QLabel("--")
        result_layout.addRow("花纹:", self._pattern_label)
        layout.addWidget(self._result_group)

        # ── Variation override ──
        override_group = QGroupBox("外观选择")
        override_layout = QFormLayout(override_group)
        self._variation_combo = QComboBox()
        self._variation_combo.addItems([
            "orange", "black", "white", "brown", "grey",
            "cream", "red", "chocolate", "blue_solid",
            "black_bicolor", "calico", "tortie", "tabby_mackerel",
        ])
        self._variation_combo.currentTextChanged.connect(self._on_variation_changed)
        override_layout.addRow("宠物外观:", self._variation_combo)
        layout.addWidget(override_group)

        # ── Progress ──
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        self._confirm_btn = QPushButton("✅ 确认")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(self._confirm_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择宠物照片", os.path.expanduser("~/Desktop"),
            "图片文件 (*.jpg *.jpeg *.png *.heic *.webp)"
        )
        if not path:
            return

        self.image_path = path
        self._preview_label.setPixmap(QPixmap())
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate

        # Load preview
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.preview_pixmap = pixmap.scaled(
                400, 190, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._preview_label.setPixmap(self.preview_pixmap)

        # Analyze in next event loop tick
        QTimer.singleShot(100, self._analyze)

    def _analyze(self):
        """Run pet analyzer on selected image."""
        if not self.image_path:
            return
        try:
            analyzer = PetAnalyzer(self.image_path)
            self.analysis_result = analyzer.analyze()
            self._show_results()
        except Exception as e:
            QMessageBox.warning(self, "识别失败", f"无法识别照片中的宠物：{e}")
            self.analysis_result = {
                "species": "cat",
                "size_group": "medium",
                "primary_color": "orange",
                "secondary_color": None,
                "pattern": "solid",
                "variation_name": "orange",
            }
            self._show_results()
        finally:
            self._progress.setVisible(False)

    def _show_results(self):
        """Display analysis results."""
        r = self.analysis_result
        self._species_label.setText(r.get("species", "猫").title())
        self._color_label.setText(f"{r.get('primary_color', '?')}" +
                                  (f" + {r['secondary_color']}" if r.get('secondary_color') else ""))
        self._pattern_label.setText(r.get("pattern", "solid"))
        self._result_group.setVisible(True)

        # Auto-set variation combo (but not if user manually changed it)
        if not self._user_changed_model:
            variation = PetAnalyzer.resolve_variation(r)
            idx = self._variation_combo.findText(variation)
            if idx >= 0:
                self._variation_combo.blockSignals(True)
                self._variation_combo.setCurrentIndex(idx)
                self._variation_combo.blockSignals(False)

        self._confirm_btn.setEnabled(True)

    def _on_variation_changed(self):
        """Track when user manually changes the variation combo."""
        self._user_changed_model = True

    def _confirm(self):
        """Confirm selection and return pet data."""
        if not self.analysis_result:
            return

        r = self.analysis_result
        selected = self._variation_combo.currentText()
        r["variation_name"] = selected

        self.result_data = r
        self.accept()
