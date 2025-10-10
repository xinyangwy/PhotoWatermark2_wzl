#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
水印设置面板
支持文本和图片水印的独立设置
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                             QLineEdit, QPushButton, QComboBox, QSlider, 
                             QCheckBox, QColorDialog, QLabel, QSpinBox,
                             QHBoxLayout, QFileDialog, QGridLayout, QFrame, QSizePolicy,
                             QScrollArea)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPixmap, QIcon
import os


class WatermarkPanel(QWidget):
    """水印设置面板"""
    
    # 设置改变信号
    settings_changed = pyqtSignal()
    
    def __init__(self, watermark_type='text'):
        super().__init__()
        self.watermark_type = watermark_type  # text 或 image
        
        # 默认设置
        self.default_settings = {
            'text': {
                'text': 'PhotoMark2',
                'font': 'Arial',
                'size': 36,
                'bold': True,
                'italic': False,
                'color': QColor(255, 255, 255),
                'opacity': 80,
                'position': 'bottom_right',
                'margin': 20,
                'rotation': 0,
                'background': False,
                'bg_color': QColor(0, 0, 0),
                'bg_opacity': 50
            },
            'image': {
                'watermark_path': '',
                'scale': 30,
                'opacity': 80,
                'position': 'bottom_right',
                'margin': 20,
                'rotation': 0,
                'tile_mode': False,
                'tile_spacing': 50
            }
        }
        
        self.current_settings = self.default_settings[self.watermark_type].copy()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI，添加滚动条以解决控件和标签显示不全的问题"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置滚动条样式使其更加明显
        scroll_area.setStyleSheet("""
            QScrollBar:vertical {
                width: 15px;
                background: #f0f0f0;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #888;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: #ccc;
                height: 10px;
                subcontrol-origin: margin;
            }
            QScrollBar::add-line:vertical:hover,
            QScrollBar::sub-line:vertical:hover {
                background: #aaa;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: #e0e0e0;
            }
        """)
        
        # 创建滚动区域的内部widget
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建主设置区域
        if self.watermark_type == 'text':
            self.create_text_watermark_ui(layout)
        else:
            self.create_image_watermark_ui(layout)
            
        # 添加位置和样式设置
        self.create_position_style_ui(layout)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # 添加导出设置
        self.create_export_ui(layout)
        
        layout.addStretch()
        
        # 将滚动内容widget设置到滚动区域
        scroll_area.setWidget(scroll_content)
        
        # 设置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
    def create_text_watermark_ui(self, layout):
        """创建文本水印UI"""
        # 文本内容设置
        text_group = QGroupBox("文本设置")
        text_layout = QFormLayout(text_group)
        
        self.text_input = QLineEdit(self.current_settings['text'])
        self.text_input.textChanged.connect(self.on_text_changed)
        text_layout.addRow("文本内容:", self.text_input)
        
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout(font_group)
        
        self.font_combo = QComboBox()
        self.font_combo.addItems(['Arial', 'Microsoft YaHei', 'SimHei', 'Times New Roman', 'Courier New'])
        self.font_combo.setCurrentText(self.current_settings['font'])
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        font_layout.addRow("字体:", self.font_combo)
        
        # 字号和样式
        size_style_layout = QHBoxLayout()
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 100)
        self.size_spin.setValue(self.current_settings['size'])
        self.size_spin.valueChanged.connect(self.on_size_changed)
        size_style_layout.addWidget(QLabel("字号:"))
        size_style_layout.addWidget(self.size_spin)
        
        self.bold_check = QCheckBox("粗体")
        self.bold_check.setChecked(self.current_settings['bold'])
        self.bold_check.toggled.connect(self.on_bold_toggled)
        size_style_layout.addWidget(self.bold_check)
        
        self.italic_check = QCheckBox("斜体")
        self.italic_check.setChecked(self.current_settings['italic'])
        self.italic_check.toggled.connect(self.on_italic_toggled)
        size_style_layout.addWidget(self.italic_check)
        
        font_layout.addRow("", size_style_layout)
        
        # 颜色设置
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        
        self.color_button = QPushButton()
        self.color_button.setFixedSize(30, 30)
        self.color_button.clicked.connect(self.select_color)
        self.update_color_button()
        color_layout.addWidget(self.color_button)
        
        self.color_label = QLabel()
        self.update_color_label()
        color_layout.addWidget(self.color_label)
        
        font_layout.addRow("", color_layout)
        
        # 透明度
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.current_settings['opacity'])
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        font_layout.addRow("透明度:", self.opacity_slider)
        
        # 背景设置
        bg_layout = QHBoxLayout()
        self.bg_check = QCheckBox("添加背景")
        self.bg_check.setChecked(self.current_settings['background'])
        self.bg_check.toggled.connect(self.on_bg_toggled)
        bg_layout.addWidget(self.bg_check)
        
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(20, 20)
        self.bg_color_button.clicked.connect(self.select_bg_color)
        self.update_bg_color_button()
        bg_layout.addWidget(self.bg_color_button)
        
        self.bg_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_opacity_slider.setRange(0, 100)
        self.bg_opacity_slider.setValue(self.current_settings['bg_opacity'])
        self.bg_opacity_slider.valueChanged.connect(self.on_bg_opacity_changed)
        bg_layout.addWidget(QLabel("背景透明度:"))
        bg_layout.addWidget(self.bg_opacity_slider)
        
        font_layout.addRow("", bg_layout)
        
        layout.addWidget(text_group)
        layout.addWidget(font_group)
        
    def create_image_watermark_ui(self, layout):
        """创建图片水印UI"""
        # 图片选择
        image_group = QGroupBox("图片设置")
        image_layout = QFormLayout(image_group)
        
        self.image_path_label = QLabel("未选择图片")
        image_layout.addRow("当前图片:", self.image_path_label)
        
        select_layout = QHBoxLayout()
        self.select_image_button = QPushButton("选择图片")
        self.select_image_button.clicked.connect(self.select_image)
        select_layout.addWidget(self.select_image_button)
        
        self.clear_image_button = QPushButton("清除")
        self.clear_image_button.clicked.connect(self.clear_image)
        select_layout.addWidget(self.clear_image_button)
        
        image_layout.addRow("", select_layout)
        
        # 预设水印
        preset_group = QGroupBox("预设水印")
        preset_layout = QVBoxLayout(preset_group)
        
        # 从resources/watermarks文件夹加载预设水印
        self.preset_watermarks = self.load_preset_watermarks()
        
        # 创建预设水印网格布局
        preset_grid_layout = QGridLayout()
        preset_grid_layout.setSpacing(5)
        
        # 添加预设水印按钮
        self.preset_buttons = []
        row, col = 0, 0
        max_cols = 4  # 每行最多显示4个预设水印
        
        for i, (name, file_path) in enumerate(self.preset_watermarks.items()):
            # 创建预设水印按钮
            preset_button = QPushButton()
            preset_button.setFixedSize(60, 60)
            preset_button.setToolTip(name)
            preset_button.clicked.connect(lambda checked, path=file_path: self.select_preset_watermark(path))
            
            # 为按钮添加文件路径属性，用于高亮显示
            preset_button.watermark_path = file_path
            
            # 加载并设置缩略图
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 缩放图片到合适大小
                scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                preset_button.setIcon(QIcon(scaled_pixmap))
                preset_button.setIconSize(scaled_pixmap.size())
            
            preset_grid_layout.addWidget(preset_button, row, col)
            self.preset_buttons.append(preset_button)
            
            # 更新行列位置
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        preset_layout.addLayout(preset_grid_layout)
        
        layout.addWidget(image_group)
        layout.addWidget(preset_group)
        
        # 缩放和透明度
        scale_opacity_group = QGroupBox("缩放和透明度")
        scale_opacity_layout = QFormLayout(scale_opacity_group)
        
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(5, 200)
        self.scale_slider.setValue(self.current_settings['scale'])
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        scale_opacity_layout.addRow("缩放比例(%):", self.scale_slider)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.current_settings['opacity'])
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        scale_opacity_layout.addRow("透明度(%):", self.opacity_slider)
        
        layout.addWidget(scale_opacity_group)
        
        # 平铺模式
        tile_group = QGroupBox("平铺设置")
        tile_layout = QFormLayout(tile_group)
        
        self.tile_check = QCheckBox("启用平铺模式")
        self.tile_check.setChecked(self.current_settings['tile_mode'])
        self.tile_check.toggled.connect(self.on_tile_toggled)
        tile_layout.addRow("", self.tile_check)
        
        self.tile_spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self.tile_spacing_slider.setRange(10, 200)
        self.tile_spacing_slider.setValue(self.current_settings['tile_spacing'])
        self.tile_spacing_slider.valueChanged.connect(self.on_tile_spacing_changed)
        tile_layout.addRow("平铺间距:", self.tile_spacing_slider)
        
        layout.addWidget(tile_group)
        
    def create_position_style_ui(self, layout):
        """创建位置和样式设置UI"""
        pos_style_group = QGroupBox("位置和样式")
        pos_style_layout = QVBoxLayout(pos_style_group)
        # 设置布局伸展因子，确保空间分配合理
        pos_style_layout.setContentsMargins(10, 10, 10, 10)
        pos_style_layout.setSpacing(10)
        
        # 位置设置
        position_group = QGroupBox("位置设置")
        position_layout = QGridLayout(position_group)
        # 设置网格布局的行列伸缩因子
        for i in range(4):  # 4行
            position_layout.setRowStretch(i, 1)
        for i in range(3):  # 3列
            position_layout.setColumnStretch(i, 1)
        position_layout.setSpacing(5)
        position_layout.setContentsMargins(10, 10, 10, 10)
        
        positions = [
            ("左上", "top_left", 0, 0), ("中上", "top_center", 0, 1), ("右上", "top_right", 0, 2),
            ("左中", "center_left", 1, 0), ("正中", "center", 1, 1), ("右中", "center_right", 1, 2),
            ("左下", "bottom_left", 2, 0), ("中下", "bottom_center", 2, 1), ("右下", "bottom_right", 2, 2),
            ("自定义", "custom", 3, 1)  # 添加自定义位置选项
        ]
        
        self.position_buttons = {}
        for text, pos, row, col in positions:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumSize(60, 30)  # 设置按钮最小尺寸
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # 设置按钮可扩展
            if pos == self.current_settings['position']:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, p=pos: self.set_position(p))
            position_layout.addWidget(btn, row, col)
            self.position_buttons[pos] = btn
        
        pos_style_layout.addWidget(position_group)
        
        # 边距设置
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("边距:"))
        
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 200)
        self.margin_spin.setValue(self.current_settings['margin'])
        self.margin_spin.valueChanged.connect(self.on_margin_changed)
        self.margin_spin.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)  # 设置可扩展
        margin_layout.addWidget(self.margin_spin)
        margin_layout.addWidget(QLabel("像素"))
        margin_layout.addStretch()  # 添加伸缩空间
        
        pos_style_layout.addLayout(margin_layout)
        
        # 旋转设置
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("旋转角度:"))
        
        self.rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotation_slider.setRange(0, 360)
        self.rotation_slider.setValue(self.current_settings['rotation'])
        self.rotation_slider.valueChanged.connect(self.on_rotation_changed)
        self.rotation_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # 设置可扩展
        rotation_layout.addWidget(self.rotation_slider)
        
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(0, 360)
        self.rotation_spin.setValue(self.current_settings['rotation'])
        self.rotation_spin.valueChanged.connect(self.on_rotation_changed)
        rotation_layout.addWidget(self.rotation_spin)
        
        pos_style_layout.addLayout(rotation_layout)
        pos_style_layout.addStretch()  # 添加伸缩空间确保底部不会被拉伸
        
        layout.addWidget(pos_style_group)
        # 设置组盒在布局中的伸展因子
        layout.setStretchFactor(pos_style_group, 1)
        
    def create_export_ui(self, layout):
        """创建导出设置UI"""
        export_group = QGroupBox("导出设置")
        export_layout = QFormLayout(export_group)
        
        # 输出路径
        path_layout = QHBoxLayout()
        self.output_path_label = QLabel("./output")
        path_layout.addWidget(QLabel("输出目录:"))
        path_layout.addWidget(self.output_path_label)
        path_layout.addStretch()
        
        self.select_output_button = QPushButton("选择目录")
        self.select_output_button.clicked.connect(self.select_output_path)
        path_layout.addWidget(self.select_output_button)
        
        export_layout.addRow("", path_layout)
        
        # 命名规则
        naming_layout = QHBoxLayout()
        naming_layout.addWidget(QLabel("命名规则:"))
        
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("前缀")
        naming_layout.addWidget(self.prefix_input)
        
        naming_layout.addWidget(QLabel("_"))
        
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("后缀")
        naming_layout.addWidget(self.suffix_input)
        
        export_layout.addRow("", naming_layout)
        
        # 格式选项
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("格式:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "BMP"])
        format_layout.addWidget(self.format_combo)
        
        format_layout.addWidget(QLabel("质量:"))
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        format_layout.addWidget(self.quality_slider)
        
        self.quality_label = QLabel("90%")
        format_layout.addWidget(self.quality_label)
        
        export_layout.addRow("", format_layout)
        
        layout.addWidget(export_group)
        
    # 文本水印相关方法
    def on_text_changed(self, text):
        """文本内容改变"""
        self.current_settings['text'] = text
        self.settings_changed.emit()
        
    def on_font_changed(self, font):
        """字体改变"""
        self.current_settings['font'] = font
        self.settings_changed.emit()
        
    def on_size_changed(self, size):
        """字号改变"""
        self.current_settings['size'] = size
        self.settings_changed.emit()
        
    def on_bold_toggled(self, checked):
        """粗体切换"""
        self.current_settings['bold'] = checked
        self.settings_changed.emit()
        
    def on_italic_toggled(self, checked):
        """斜体切换"""
        self.current_settings['italic'] = checked
        self.settings_changed.emit()
        
    def select_color(self):
        """选择颜色"""
        # 检查color类型，如果是字符串则转换为QColor对象
        initial_color = self.current_settings['color']
        if isinstance(initial_color, str):
            initial_color = QColor(initial_color)
            # 如果字符串无法转换为有效的颜色，则使用默认白色
            if not initial_color.isValid():
                initial_color = QColor(255, 255, 255)  # 默认白色
                self.current_settings['color'] = initial_color
        
        color = QColorDialog.getColor(initial_color, self, "选择颜色")
        if color.isValid():
            self.current_settings['color'] = color
            self.update_color_button()
            self.update_color_label()
            self.settings_changed.emit()
            
    def update_color_button(self):
        """更新颜色按钮显示"""
        color = self.current_settings['color']
        self.color_button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc;")
        
    def update_color_label(self):
        """更新颜色标签显示"""
        color = self.current_settings['color']
        self.color_label.setText(f"RGB({color.red()}, {color.green()}, {color.blue()})")
        
    def on_opacity_changed(self, value):
        """透明度改变"""
        self.current_settings['opacity'] = value
        self.settings_changed.emit()
        
    def on_bg_toggled(self, checked):
        """背景切换"""
        self.current_settings['background'] = checked
        self.settings_changed.emit()
        
    def select_bg_color(self):
        """选择背景颜色"""
        color = QColorDialog.getColor(self.current_settings['bg_color'], self, "选择背景颜色")
        if color.isValid():
            self.current_settings['bg_color'] = color
            self.update_bg_color_button()
            self.settings_changed.emit()
            
    def update_bg_color_button(self):
        """更新背景颜色按钮显示"""
        color = self.current_settings['bg_color']
        self.bg_color_button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc;")
        
    def on_bg_opacity_changed(self, value):
        """背景透明度改变"""
        self.current_settings['bg_opacity'] = value
        self.settings_changed.emit()
        
    # 图片水印相关方法
    def select_image(self):
        """选择图片水印"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择水印图片", 
            "", 
            "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            self.current_settings['watermark_path'] = file_path
            self.image_path_label.setText(os.path.basename(file_path))
            self.settings_changed.emit()
            
    def clear_image(self):
        """清除图片水印"""
        self.current_settings['watermark_path'] = ''
        self.image_path_label.setText("未选择图片")
        self.settings_changed.emit()
        
    def on_scale_changed(self, value):
        """缩放比例改变"""
        self.current_settings['scale'] = value
        self.settings_changed.emit()
        
    def on_tile_toggled(self, checked):
        """平铺模式切换"""
        self.current_settings['tile_mode'] = checked
        self.settings_changed.emit()
        
    def on_tile_spacing_changed(self, value):
        """平铺间距改变"""
        self.current_settings['tile_spacing'] = value
        self.settings_changed.emit()
        
    # 位置和样式相关方法
    def set_position(self, position):
        """设置位置"""
        # 取消其他按钮的选中状态
        for pos, btn in self.position_buttons.items():
            btn.setChecked(pos == position)
        
        self.current_settings['position'] = position
        self.settings_changed.emit()
        
    def on_margin_changed(self, value):
        """边距改变"""
        self.current_settings['margin'] = value
        self.settings_changed.emit()
        
    def on_rotation_changed(self, value):
        """旋转角度改变"""
        self.current_settings['rotation'] = value
        self.rotation_slider.setValue(value)
        self.rotation_spin.setValue(value)
        self.settings_changed.emit()
        
    # 导出设置相关方法
    def select_output_path(self):
        """选择输出路径"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录", "./output")
        if dir_path:
            self.output_path_label.setText(dir_path)
            
    def on_quality_changed(self, value):
        """质量改变"""
        self.quality_label.setText(f"{value}%")
        
    def get_settings(self):
        """获取当前设置"""
        return self.current_settings.copy()
        
    def set_settings(self, settings):
        """应用设置"""
        self.current_settings.update(settings)
        # 这里应该更新UI控件状态
        self.settings_changed.emit()
    
    def update_position_from_drag(self, x: int, y: int):
        """从拖拽操作更新位置设置"""
        # 设置位置为自定义模式，并保存坐标
        self.current_settings['position'] = 'custom'
        self.current_settings['custom_x'] = x
        self.current_settings['custom_y'] = y
        
        # 直接设置x和y坐标，用于实时预览
        self.current_settings['x'] = x
        self.current_settings['y'] = y
        
        # 更新位置按钮状态
        for pos, btn in self.position_buttons.items():
            btn.setChecked(pos == 'custom')
            
        # 如果没有位置输入框，创建它们
        if not hasattr(self, 'position_x_spin') or not hasattr(self, 'position_y_spin'):
            self.create_position_inputs()
        else:
            # 更新位置输入框
            self.position_x_spin.blockSignals(True)
            self.position_y_spin.blockSignals(True)
            self.position_x_spin.setValue(x)
            self.position_y_spin.setValue(y)
            self.position_x_spin.blockSignals(False)
            self.position_y_spin.blockSignals(False)
        
        # 发送设置变更信号，触发实时预览
        self.settings_changed.emit()
        
    def create_position_inputs(self):
        """创建自定义位置输入框"""
        # 查找位置设置组
        for child in self.findChildren(QGroupBox):
            if child.title() == "位置设置":
                position_group = child
                break
        else:
            return
        
        # 查找布局
        position_layout = position_group.layout()
        if not position_layout:
            return
        
        # 检查是否已经存在自定义位置输入框
        if hasattr(self, 'position_x_spin'):
            return
        
        # 创建位置输入框布局
        pos_input_layout = QHBoxLayout()
        pos_input_layout.addWidget(QLabel("X坐标:"))
        
        self.position_x_spin = QSpinBox()
        self.position_x_spin.setRange(0, 9999)
        self.position_x_spin.setValue(self.current_settings.get('custom_x', 0))
        self.position_x_spin.setMinimumWidth(60)
        self.position_x_spin.valueChanged.connect(self.on_custom_x_changed)
        pos_input_layout.addWidget(self.position_x_spin)
        
        pos_input_layout.addWidget(QLabel("Y坐标:"))
        
        self.position_y_spin = QSpinBox()
        self.position_y_spin.setRange(0, 9999)
        self.position_y_spin.setValue(self.current_settings.get('custom_y', 0))
        self.position_y_spin.setMinimumWidth(60)
        self.position_y_spin.valueChanged.connect(self.on_custom_y_changed)
        pos_input_layout.addWidget(self.position_y_spin)
        
        pos_input_layout.addStretch()
        
        # 在位置设置组底部添加输入框
        # 找到自定义位置按钮的位置
        custom_btn = self.position_buttons.get('custom')
        if custom_btn:
            # 获取按钮的行号
            index = position_layout.indexOf(custom_btn)
            row, col, row_span, col_span = position_layout.getItemPosition(index)
            # 在按钮下方添加输入框
            position_layout.addLayout(pos_input_layout, row + 1, 0, 1, 3)
    
    def on_custom_x_changed(self, value):
        """自定义X坐标改变"""
        self.current_settings['custom_x'] = value
        self.current_settings['x'] = value
        self.settings_changed.emit()
        
    def on_custom_y_changed(self, value):
        """自定义Y坐标改变"""
        self.current_settings['custom_y'] = value
        self.current_settings['y'] = value
        self.settings_changed.emit()
    
    # 预设水印相关方法
    def load_preset_watermarks(self):
        """加载预设水印图片"""
        preset_watermarks = {}
        watermarks_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'watermarks')
        
        if os.path.exists(watermarks_dir):
            # 支持的图片格式
            image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
            
            for filename in os.listdir(watermarks_dir):
                if filename.lower().endswith(image_extensions):
                    file_path = os.path.join(watermarks_dir, filename)
                    # 使用文件名（不含扩展名）作为显示名称
                    name = os.path.splitext(filename)[0]
                    preset_watermarks[name] = file_path
        
        return preset_watermarks
    
    def select_preset_watermark(self, file_path):
        """选择预设水印"""
        if os.path.exists(file_path):
            self.current_settings['watermark_path'] = file_path
            self.image_path_label.setText(os.path.basename(file_path))
            self.settings_changed.emit()
            
            # 可选：添加一些视觉反馈，比如高亮选中的预设水印
            self.highlight_selected_preset(file_path)
    
    def highlight_selected_preset(self, selected_path):
        """高亮显示选中的预设水印"""
        for button in self.preset_buttons:
            # 重置所有按钮样式
            button.setStyleSheet("")
            
            # 检查这个按钮对应的文件路径
            # 由于我们无法直接从按钮获取文件路径，我们需要通过其他方式关联
            # 这里我们简单地为所有按钮添加一个属性来存储文件路径
            if hasattr(button, 'watermark_path') and button.watermark_path == selected_path:
                button.setStyleSheet("border: 2px solid #0078d4; background-color: #f0f0f0;")