#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片水印工具主应用
提供现代化的GUI界面，支持批量处理和实时预览
"""

import sys
import os
import logging
import json
from typing import List, Dict, Any
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QFileDialog, QMessageBox,
                             QMenuBar, QMenu, QStatusBar, QToolBar, QTabWidget,
                             QProgressBar, QLabel, QPushButton, QFrame, QScrollArea,
                             QLineEdit, QComboBox, QSlider)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot, QPoint
from PyQt6.QtGui import QIcon, QAction, QPixmap, QFont

from src.ui.image_list_panel import ImageListPanel
from src.ui.preview_panel import PreviewPanel
from src.ui.watermark_panel import WatermarkPanel
from src.core.watermark_processor import WatermarkProcessor
from src.utils.config_manager import ConfigManager
from src.utils.resource_manager import ResourceManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImportImagesThread(QThread):
    """异步导入图片线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度，文件名
    finished_signal = pyqtSignal(list)  # 导入成功的图片路径列表
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self, image_paths: List[str], parent=None):
        super().__init__(parent)
        self.image_paths = image_paths
        self._is_running = True
    
    def run(self):
        """执行异步导入"""
        try:
            valid_images = []
            total = len(self.image_paths)
            
            # 批量验证文件存在性和扩展名，这是最快的验证方式
            for i, image_path in enumerate(self.image_paths):
                if not self._is_running:
                    break
                    
                filename = os.path.basename(image_path)
                self.progress_updated.emit(int((i + 1) / total * 100), filename)
                
                try:
                    # 验证图片文件
                    if not os.path.exists(image_path):
                        logger.warning(f"文件不存在: {image_path}")
                        continue
                    
                    # 检查文件扩展名
                    valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
                    if not any(image_path.lower().endswith(ext) for ext in valid_extensions):
                        logger.warning(f"不支持的图片格式: {image_path}")
                        continue
                    
                    # 快速检查文件头，提高验证速度
                    # 对于大多数情况，文件扩展名检查已经足够
                    # 只在必要时（批量导入特别大的文件夹）才进行完整加载验证
                    try:
                        # 只读取文件头几个字节进行快速验证
                        with open(image_path, 'rb') as f:
                            file_header = f.read(12)
                        
                        # 检查常见图片格式的文件头特征
                        is_valid = False
                        # PNG 文件头
                        if file_header.startswith(b'\x89PNG\r\n\x1a\n'):
                            is_valid = True
                        # JPEG 文件头
                        elif file_header.startswith(b'\xff\xd8'):
                            is_valid = True
                        # BMP 文件头
                        elif file_header.startswith(b'BM'):
                            is_valid = True
                        # GIF 文件头
                        elif file_header.startswith(b'GIF8'):
                            is_valid = True
                        # WebP 文件头
                        elif len(file_header) >= 12 and file_header.startswith(b'RIFF') and file_header[8:12] == b'WEBP':
                            is_valid = True
                        # TIFF 文件头
                        elif file_header.startswith(b'II') or file_header.startswith(b'MM'):
                            is_valid = True
                        
                        # 如果文件头检查失败或不支持的格式，尝试完整加载（作为后备）
                        if not is_valid:
                            try:
                                # 使用 QPixmap.loadFromData 来验证，而不是加载整个文件
                                with open(image_path, 'rb') as f:
                                    # 只读取文件的一小部分进行验证
                                    sample_data = f.read(1024 * 1024)  # 读取1MB用于验证
                                pixmap = QPixmap()
                                if pixmap.loadFromData(sample_data):
                                    is_valid = True
                                else:
                                    logger.warning(f"文件头检查失败，但可能是有效图片，将在缩略图加载时进一步验证: {image_path}")
                                    is_valid = True  # 保留此文件，让缩略图加载器进一步验证
                            except Exception as e:
                                logger.warning(f"文件验证失败: {image_path}, 错误: {str(e)}")
                                is_valid = False
                        
                        if is_valid:
                            valid_images.append(image_path)
                        else:
                            logger.warning(f"无效的图片文件: {image_path}")
                    except Exception as e:
                        logger.error(f"验证图片文件头失败 {image_path}: {str(e)}")
                        # 如果文件头检查失败，尝试完整加载作为后备
                        try:
                            pixmap = QPixmap(image_path)
                            if not pixmap.isNull():
                                valid_images.append(image_path)
                            else:
                                logger.warning(f"无法加载图片: {image_path}")
                        except Exception:
                            pass
                        
                except Exception as e:
                    logger.error(f"验证图片失败 {image_path}: {str(e)}")
            
            self.finished_signal.emit(valid_images)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def stop(self):
        """停止导入"""
        self._is_running = False


class BatchProcessThread(QThread):
    """批量处理线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度，文件名
    finished_signal = pyqtSignal(dict)  # 处理结果
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self, processor: WatermarkProcessor, image_paths: List[str], 
                 settings: Dict[str, Any], output_dir: str, watermark_type: str):
        super().__init__()
        self.processor = processor
        self.image_paths = image_paths
        self.settings = settings
        self.output_dir = output_dir
        self.watermark_type = watermark_type
        self._is_running = True
    
    def run(self):
        """执行批量处理"""
        try:
            results = {}
            total = len(self.image_paths)
            
            # 创建一个settings副本并添加日志级别设置
            settings_copy = self.settings.copy()
            settings_copy['log_level'] = 'debug'  # 批量处理时使用debug级别日志
            
            for i, image_path in enumerate(self.image_paths):
                if not self._is_running:
                    break
                    
                filename = os.path.basename(image_path)
                self.progress_updated.emit(int((i + 1) / total * 100), filename)
                
                try:
                    if self.watermark_type == 'text':
                        result_pixmap = self.processor.add_text_watermark(
                            image_path, settings_copy.get('text', ''), settings_copy)
                    else:
                        result_pixmap = self.processor.add_image_watermark(
                            image_path, settings_copy.get('watermark_path', ''), settings_copy)
                    
                    if result_pixmap and not result_pixmap.isNull():
                        # 使用批量导出设置中的命名规则和格式（优先级高于水印面板中的设置）
                        name, ext = os.path.splitext(filename)
                        
                        # 应用前缀和后缀
                        prefix = settings_copy.get('prefix', '')
                        suffix = settings_copy.get('suffix', '')
                        
                        # 构建新的文件名
                        if prefix and suffix:
                            output_basename = f"{prefix}_{name}_{suffix}"
                        elif prefix:
                            output_basename = f"{prefix}_{name}"
                        elif suffix:
                            output_basename = f"{name}_{suffix}"
                        else:
                            output_basename = name  # 没有设置前缀和后缀时保留原始文件名
                        
                        # 应用格式设置
                        format_setting = settings_copy.get('format', '')
                        if format_setting:
                            # 根据格式设置调整扩展名
                            format_lower = format_setting.lower()
                            if format_lower == 'jpeg':
                                output_ext = '.jpg'
                            elif format_lower == 'png':
                                output_ext = '.png'
                            elif format_lower == 'bmp':
                                output_ext = '.bmp'
                            else:
                                output_ext = ext
                        else:
                            output_ext = ext
                        
                        output_filename = f"{output_basename}{output_ext}"
                        output_path = os.path.join(self.output_dir, output_filename)
                        
                        # 保存图片时考虑格式和质量设置
                        quality = settings_copy.get('quality', 90)
                        if format_setting:
                            # 设置质量参数，主要对JPEG格式有效
                            result_pixmap.save(output_path, format_setting, quality)
                        else:
                            result_pixmap.save(output_path, quality=quality)
                        
                        results[image_path] = output_path
                        
                except Exception as e:
                    logger.error(f"处理图片失败 {image_path}: {str(e)}")
            
            self.finished_signal.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def stop(self):
        """停止处理"""
        self._is_running = False


class PhotoMarkApp(QMainWindow):
    """图片水印工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片水印工具 - PhotoMark")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化核心组件
        self.watermark_processor = WatermarkProcessor()
        self.config_manager = ConfigManager()
        self.resource_manager = ResourceManager()
        
        # 设置应用图标
        app_icon = self.resource_manager.get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        
        # 当前状态
        self.current_image_path = None
        self.image_paths = []
        self.batch_thread = None
        self.import_thread = None  # 异步导入线程
        
        # 创建界面
        self.init_ui()

        # 主设置，用于批量处理和在切换图片时重置面板
        self.master_text_settings = self.text_watermark_panel.get_settings()
        self.master_image_settings = self.image_watermark_panel.get_settings()
        
        # 加载配置
        self.load_config()
        
        # 状态栏显示欢迎信息
        self.statusbar.showMessage("欢迎使用图片水印工具 - 请导入图片开始处理")
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建主内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        content_layout.addWidget(splitter)
        
        # 左侧面板 - 图片列表
        self.image_list_panel = ImageListPanel()
        splitter.addWidget(self.image_list_panel)
        
        # 预览面板
        self.preview_panel = PreviewPanel()
        splitter.addWidget(self.preview_panel)
        
        # 右侧面板 - 水印设置（使用标签页）
        self.create_settings_tabs()
        splitter.addWidget(self.settings_tabs)
        
        # 设置分割器比例
        splitter.setSizes([250, 500, 350])
        
        main_layout.addWidget(content_widget)
        
        # 创建底部状态栏
        self.create_status_bar()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 连接信号槽
        self.connect_signals()
        
        # 连接水印位置拖拽信号
        self.preview_panel.watermark_position_changed.connect(self.on_watermark_position_changed)
    
    def create_top_toolbar(self):
        """创建顶部工具栏"""
        self.top_toolbar = QToolBar("顶部工具栏")
        self.top_toolbar.setMovable(False)
        self.top_toolbar.setIconSize(QSize(32, 32))
        self.top_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        

        

    
    def create_settings_tabs(self):
        """创建设置标签页"""
        self.settings_tabs = QTabWidget()
        
        # 文本水印标签页
        self.text_watermark_panel = WatermarkPanel(watermark_type='text')
        self.settings_tabs.addTab(self.text_watermark_panel, "文本水印")
        
        # 图片水印标签页
        self.image_watermark_panel = WatermarkPanel(watermark_type='image')
        self.settings_tabs.addTab(self.image_watermark_panel, "图片水印")
        
        # 批量导出设置标签页
        self.batch_panel = self.create_batch_panel()
        self.settings_tabs.addTab(self.batch_panel, "批量导出设置")
        
        # 连接标签页切换信号，记录最后活动的水印类型
        self.settings_tabs.currentChanged.connect(self.on_tab_changed)
        
        # 设置默认水印类型
        self._last_active_watermark_type = 'text'
    
    def create_batch_panel(self) -> QWidget:
        """创建批量导出设置面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 输出目录设置
        output_group = QFrame()
        output_group.setFrameStyle(QFrame.Shape.StyledPanel)
        output_layout = QVBoxLayout(output_group)
        
        output_label = QLabel("输出目录:")
        output_layout.addWidget(output_label)
        
        output_hbox = QHBoxLayout()
        self.output_path_label = QLabel("未设置")
        self.output_path_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
        output_hbox.addWidget(self.output_path_label)
        
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.choose_output_directory)
        output_hbox.addWidget(browse_btn)
        
        output_layout.addLayout(output_hbox)
        layout.addWidget(output_group)
        
        # 导出设置
        export_group = QFrame()
        export_group.setFrameStyle(QFrame.Shape.StyledPanel)
        export_layout = QVBoxLayout(export_group)
        
        export_label = QLabel("导出设置:")
        export_layout.addWidget(export_label)
        
        # 命名规则
        naming_layout = QHBoxLayout()
        naming_layout.addWidget(QLabel("命名规则:"))
        
        self.batch_prefix_input = QLineEdit()
        self.batch_prefix_input.setPlaceholderText("前缀")
        naming_layout.addWidget(self.batch_prefix_input)
        
        naming_layout.addWidget(QLabel("_"))
        
        self.batch_suffix_input = QLineEdit()
        self.batch_suffix_input.setPlaceholderText("后缀")
        naming_layout.addWidget(self.batch_suffix_input)
        
        export_layout.addLayout(naming_layout)
        
        # 格式选项
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("格式:"))
        
        self.batch_format_combo = QComboBox()
        self.batch_format_combo.addItems(["JPEG", "PNG", "BMP"])
        format_layout.addWidget(self.batch_format_combo)
        
        export_layout.addLayout(format_layout)
        
        # 质量选项
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("质量:"))
        
        self.batch_quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.batch_quality_slider.setRange(1, 100)
        self.batch_quality_slider.setValue(90)  # 默认高质量
        self.batch_quality_slider.setTickInterval(10)
        self.batch_quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        quality_layout.addWidget(self.batch_quality_slider)
        
        self.batch_quality_label = QLabel("90%")
        quality_layout.addWidget(self.batch_quality_label)
        
        # 连接滑块信号
        self.batch_quality_slider.valueChanged.connect(self.on_quality_changed)
        
        export_layout.addLayout(quality_layout)
        
        layout.addWidget(export_group)
        
        # 进度显示
        progress_group = QFrame()
        progress_group.setFrameStyle(QFrame.Shape.StyledPanel)
        progress_layout = QVBoxLayout(progress_group)
        
        progress_label = QLabel("处理进度:")
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.start_batch_btn = QPushButton("开始批量导出")
        self.start_batch_btn.clicked.connect(self.start_batch_process)
        button_layout.addWidget(self.start_batch_btn)
        
        self.stop_batch_btn = QPushButton("停止处理")
        self.stop_batch_btn.clicked.connect(self.stop_batch_process)
        self.stop_batch_btn.setEnabled(False)
        button_layout.addWidget(self.stop_batch_btn)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return panel
    
    def create_status_bar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # 添加图片计数
        self.image_count_label = QLabel("图片: 0")
        self.statusbar.addPermanentWidget(self.image_count_label)
        
        # 添加版本信息
        version_label = QLabel("PhotoMark v2.0")
        self.statusbar.addPermanentWidget(version_label)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        import_action = QAction('导入图片', self)
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.import_images)
        file_menu.addAction(import_action)
        
        import_folder_action = QAction('导入文件夹', self)
        import_folder_action.setShortcut('Ctrl+Shift+I')
        import_folder_action.triggered.connect(self.import_folder)
        file_menu.addAction(import_folder_action)
        
        file_menu.addSeparator()
        
        batch_action = QAction('批量处理', self)
        batch_action.setShortcut('Ctrl+B')
        batch_action.triggered.connect(self.batch_process)
        file_menu.addAction(batch_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        clear_action = QAction('清除所有图片', self)
        clear_action.triggered.connect(self.clear_images)
        edit_menu.addAction(clear_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        preview_action = QAction('预览效果', self)
        preview_action.setShortcut('Ctrl+P')
        preview_action.triggered.connect(self.preview_watermark)
        view_menu.addAction(preview_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('保存或加载模板')
        
        save_settings_action = QAction('保存模板', self)
        save_settings_action.triggered.connect(self.save_settings)
        settings_menu.addAction(save_settings_action)
        
        load_settings_action = QAction('加载模板', self)
        load_settings_action.triggered.connect(self.load_settings)
        settings_menu.addAction(load_settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def connect_signals(self):
        """连接信号槽"""
        # 图片列表信号
        self.image_list_panel.image_selected.connect(self.on_image_selected)
        self.image_list_panel.image_list_changed.connect(self.on_image_list_changed)
        
        # 水印面板信号
        self.text_watermark_panel.settings_changed.connect(self.on_settings_changed)
        self.image_watermark_panel.settings_changed.connect(self.on_settings_changed)
        
        # 预览面板位置变化信号
        self.preview_panel.position_changed.connect(self.on_watermark_position_changed)
    
    @pyqtSlot(str)
    def on_image_selected(self, image_path: str):
        """当从列表中选择新图片时的处理 - 优化版"""
        if not image_path or not os.path.exists(image_path):
            self.current_image_path = None
            self.preview_panel.clear()
            self.statusbar.showMessage("无效的图片选择")
            return

        self.current_image_path = image_path
        self.statusbar.showMessage(f"已选择图片: {os.path.basename(image_path)}")

        # 首先快速设置原图预览
        self.preview_panel.set_image(image_path)
        
        # 检查当前面板的设置
        current_tab_index = self.settings_tabs.currentIndex()
        if current_tab_index in [0, 1]:  # Text or Image
            panel = self.settings_tabs.currentWidget()
            
            # 只有在明确勾选了"应用到全部"时，才更新面板设置为master设置
            if panel.get_settings().get('apply_to_all', False):
                if current_tab_index == 0:
                    panel.set_settings(self.master_text_settings.copy())
                else:
                    panel.set_settings(self.master_image_settings.copy())
            else:
                # 当没有勾选"应用到全部"时，应用默认水印设置
                if current_tab_index == 0:
                    panel.set_settings(panel.default_settings['text'].copy())
                else:
                    panel.set_settings(panel.default_settings['image'].copy())
            
            # 设置标记表示这是由于图片切换引起的预览
            self._is_image_switching = True
            # 异步生成水印预览，避免阻塞UI
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.preview_watermark)
        elif current_tab_index == 2: # Batch panel
            # 异步生成水印预览
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.preview_watermark)
    
    @pyqtSlot(list)
    def on_image_list_changed(self, image_paths: list):
        """图片列表改变"""
        self.image_paths = image_paths
        self.update_image_count()
    
    @pyqtSlot()
    def on_settings_changed(self):
        """当水印设置改变时调用"""
        current_tab_index = self.settings_tabs.currentIndex()
        if current_tab_index not in [0, 1]:  # 仅处理文本和图片水印面板
            return

        panel = self.settings_tabs.currentWidget()
        settings = panel.get_settings()

        # 只在明确勾选了"应用到全部图片"时才更新主设置
        if settings.get('apply_to_all', False):
            # 深拷贝确保主设置和面板设置是独立的对象
            if current_tab_index == 0:
                self.master_text_settings = settings.copy()
            else:
                self.master_image_settings = settings.copy()
            self.statusbar.showMessage("水印设置已更新，将应用于所有图片")
        else:
            # 未勾选"应用到全部图片"时，这只是一个临时的预览更改，不更新主设置
            self.statusbar.showMessage("水印设置已更新，仅应用于当前预览图片")

        # 始终更新预览，但不影响其他图片
        if self.current_image_path:
            self.preview_watermark()
    

    
    def import_images(self):
        """异步导入图片"""
        try:
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif);;所有文件 (*)")
            
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    self.start_async_import(selected_files, "导入图片")
        except Exception as e:
            logger.error(f"导入图片失败: {str(e)}")
            QMessageBox.critical(self, "导入错误", f"导入图片时发生错误:\n{str(e)}")
    
    def import_folder(self):
        """异步导入文件夹"""
        try:
            folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
            if folder_path:
                # 收集文件夹中的所有图片文件
                image_files = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
                        if any(file.lower().endswith(ext) for ext in valid_extensions):
                            image_files.append(os.path.join(root, file))
                
                if image_files:
                    self.start_async_import(image_files, "导入文件夹")
                else:
                    QMessageBox.warning(self, "无图片文件", "所选文件夹中没有找到支持的图片文件")
        except Exception as e:
            logger.error(f"导入文件夹失败: {str(e)}")
            QMessageBox.critical(self, "导入错误", f"导入文件夹时发生错误:\n{str(e)}")
            
    @pyqtSlot(QPoint)
    def on_watermark_position_changed(self, position):
        """处理水印位置拖拽改变事件"""
        logger.debug(f"水印位置改变: x={position.x()}, y={position.y()}")
        
        # 获取当前活动的水印面板
        current_tab_index = self.settings_tabs.currentIndex()
        
        if current_tab_index == 0:  # 文本水印
            self.text_watermark_panel.update_position_from_drag(position)
        elif current_tab_index == 1:  # 图片水印
            self.image_watermark_panel.update_position_from_drag(position)
        
        # 刷新预览
        self.preview_watermark()
    
    def start_async_import(self, image_paths: List[str], operation_name: str):
        """开始异步导入"""
        # 停止之前的导入线程
        if self.import_thread and self.import_thread.isRunning():
            self.import_thread.stop()
            self.import_thread.wait()
        

        
        # 启动导入线程
        self.import_thread = ImportImagesThread(image_paths, self)
        self.import_thread.progress_updated.connect(self.on_import_progress)
        self.import_thread.finished_signal.connect(self.on_import_finished)
        self.import_thread.error_occurred.connect(self.on_import_error)
        
        self.statusbar.showMessage(f"{operation_name}中... (0/{len(image_paths)})")
        self.import_thread.start()
    
    @pyqtSlot(int, str)
    def on_import_progress(self, progress: int, filename: str):
        """导入进度更新"""
        # 更新状态栏
        image_paths = self.import_thread.image_paths if self.import_thread else []
        total_count = len(image_paths) if image_paths else 0
        current_count = int((progress / 100) * total_count) if total_count > 0 else 0
        self.statusbar.showMessage(f"导入中... ({current_count}/{total_count}) - {filename}")
    
    @pyqtSlot(list)
    def on_import_finished(self, valid_images: List[str]):
        """导入完成"""

        
        if valid_images:
            # 批量添加到图片列表
            self.image_list_panel.add_images(valid_images)
            
            success_count = len(valid_images)
            total_count = len(self.import_thread.image_paths) if self.import_thread else 0
            
            self.statusbar.showMessage(f"导入完成! 成功: {success_count}/{total_count} 张图片")
            
            if success_count < total_count:
                QMessageBox.information(self, "导入完成", 
                                      f"导入完成!\n成功: {success_count} 张\n失败: {total_count - success_count} 张")
            else:
                QMessageBox.information(self, "导入成功", f"成功导入 {success_count} 张图片")
        else:
            self.statusbar.showMessage("导入完成，但没有有效的图片")
            QMessageBox.warning(self, "导入失败", "没有找到有效的图片文件")
    
    @pyqtSlot(str)
    def on_import_error(self, error_msg: str):
        """导入错误"""

        
        logger.error(f"导入错误: {error_msg}")
        QMessageBox.critical(self, "导入错误", f"导入过程中发生错误:\n{error_msg}")
        self.statusbar.showMessage("导入失败")
    
    def preview_watermark(self):
        """预览水印效果 - 确保只应用于当前图片，不影响批量处理设置"""
        if not self.current_image_path:
            QMessageBox.information(self, "预览", "请先选择一张图片")
            return
        
        current_tab = self.settings_tabs.currentIndex()
        
        try:
            if current_tab == 0:  # 文本水印
                # 获取设置的深拷贝，避免修改原始设置
                settings = self.text_watermark_panel.get_settings()
                # 创建预览专用设置副本
                preview_settings = settings.copy()
                # 预览模式下设置较低的日志级别，避免过多日志
                preview_settings['log_level'] = 'debug'
                # 确保预览只应用于当前图片
                preview_settings['apply_to_all'] = False
                result_pixmap = self.watermark_processor.add_text_watermark(
                    self.current_image_path, preview_settings.get('text', ''), preview_settings)
            elif current_tab == 1:  # 图片水印
                # 获取设置的深拷贝，避免修改原始设置
                settings = self.image_watermark_panel.get_settings()
                watermark_path = settings.get('watermark_path', '')
                if not watermark_path or not os.path.exists(watermark_path):
                    # 当选择新图片时，如果没有选择水印图片，则自动选择预设水印的第一个图片
                    if hasattr(self, '_is_image_switching') and self._is_image_switching:
                        # 获取预设水印
                        preset_watermarks = self.image_watermark_panel.load_preset_watermarks()
                        if preset_watermarks:
                            # 选择第一个预设水印
                            first_watermark_path = next(iter(preset_watermarks.values()))
                            # 更新设置
                            self.image_watermark_panel.current_settings['watermark_path'] = first_watermark_path
                            self.image_watermark_panel.image_path_label.setText(os.path.basename(first_watermark_path))
                            # 重新获取设置
                            settings = self.image_watermark_panel.get_settings()
                            watermark_path = first_watermark_path
                        else:
                            # 没有预设水印，不显示错误消息
                            self._is_image_switching = False
                            return
                    else:
                        # 只有用户主动点击预览按钮时才显示错误
                        QMessageBox.warning(self, "预览失败", "请先选择有效的水印图片")
                    self._is_image_switching = False
                    # 如果没有选择水印图片，且不是由于图片切换引起的，或者没有可用的预设水印，则返回
                    if not watermark_path or not os.path.exists(watermark_path):
                        return
                # 创建预览专用设置副本
                preview_settings = settings.copy()
                # 预览模式下设置较低的日志级别，避免过多日志
                preview_settings['log_level'] = 'debug'
                # 确保预览只应用于当前图片
                preview_settings['apply_to_all'] = False
                result_pixmap = self.watermark_processor.add_image_watermark(
                    self.current_image_path, watermark_path, preview_settings)
            else:
                return
            
            if result_pixmap and not result_pixmap.isNull():
                self.preview_panel.set_watermarked_image(result_pixmap)
                self.statusbar.showMessage("水印预览已更新，仅应用于当前图片")
            else:
                QMessageBox.warning(self, "预览失败", "无法生成水印预览")
                
        except Exception as e:
            logger.error(f"预览水印失败: {str(e)}")
            QMessageBox.critical(self, "预览错误", f"预览时发生错误: {str(e)}")
    
    def batch_process(self):
        """批量处理对话框"""
        image_paths = self.image_list_panel.get_image_paths()
        if not image_paths:
            QMessageBox.information(self, "批量处理", "请先导入要处理的图片")
            return
        
        # 确保已选择输出目录
        if not hasattr(self, 'output_directory') or not self.output_directory:
            self.choose_output_directory()
            if not hasattr(self, 'output_directory') or not self.output_directory:
                return
        
        reply = QMessageBox.question(self, "批量处理", 
                                   f"将处理 {len(image_paths)} 张图片到目录:\n{self.output_directory}\n\n是否继续?")
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_batch_process()
    
    def choose_output_directory(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_directory = directory
            self.output_path_label.setText(directory)
    
    def start_batch_process(self):
        """开始批量导出"""
        image_paths = self.image_list_panel.get_image_paths()
        if not image_paths:
            QMessageBox.information(self, "批量导出", "没有图片需要处理")
            return
        
        if not hasattr(self, 'output_directory') or not self.output_directory:
            QMessageBox.warning(self, "批量导出", "请先选择输出目录")
            return
        
        # 获取当前设置 - 无论当前选中哪个标签页，都能获取有效的水印设置
        current_tab = self.settings_tabs.currentIndex()
        
        # 检查并设置默认水印类型（优先使用最近活动的水印类型）
        watermark_type = None
        if hasattr(self, '_last_active_watermark_type'):
            watermark_type = self._last_active_watermark_type
        
        # 如果没有记录的水印类型，或者当前明确选中了水印标签页，则使用当前标签页
        if not watermark_type or current_tab in (0, 1):
            watermark_type = 'text' if current_tab == 0 else 'image' if current_tab == 1 else 'text'  # 默认文本水印
        
        # 根据水印类型获取设置
        if watermark_type == 'text':
            settings = self.text_watermark_panel.get_settings()
        else:
            settings = self.image_watermark_panel.get_settings()
            watermark_path = settings.get('watermark_path', '')
            if not watermark_path or not os.path.exists(watermark_path):
                QMessageBox.warning(self, "批量处理", "请先选择有效的水印图片")
                return
        
        # 检查是否勾选了应用到全部图片
        if not settings.get('apply_to_all', False):
            QMessageBox.information(self, "批量处理", "请先勾选'是否应用到全部图片'选项")
            return
        
        # 检查并应用批量导出设置中的命名规则和格式，优先级高于水印面板中的设置
        if hasattr(self, 'batch_prefix_input') and hasattr(self, 'batch_suffix_input') and hasattr(self, 'batch_format_combo'):
            # 获取批量导出设置中的命名规则和格式
            batch_prefix = self.batch_prefix_input.text()
            batch_suffix = self.batch_suffix_input.text()
            batch_format = self.batch_format_combo.currentText()
            
            # 将批量导出设置应用到settings中，优先级高于水印面板中的设置
            if batch_prefix:
                settings['prefix'] = batch_prefix
            if batch_suffix:
                settings['suffix'] = batch_suffix
            if batch_format:
                settings['format'] = batch_format
        
        # 应用图片质量设置
        if hasattr(self, 'batch_quality_slider'):
            settings['quality'] = self.batch_quality_slider.value()
        
        # 记录日志，表明正在使用应用到所有图片的设置
        logger.info(f"开始批量处理 {len(image_paths)} 张图片，使用应用到所有图片的设置")
        

        
        # 启动处理线程
        self.batch_thread = BatchProcessThread(
            self.watermark_processor, image_paths, settings, 
            self.output_directory, watermark_type
        )
        
        self.batch_thread.progress_updated.connect(self.on_batch_progress)
        self.batch_thread.finished_signal.connect(self.on_batch_finished)
        self.batch_thread.error_occurred.connect(self.on_batch_error)
        
        # 更新UI状态
        self.start_batch_btn.setEnabled(False)
        self.stop_batch_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.batch_thread.start()
        self.statusbar.showMessage("批量处理已开始...")
    
    def stop_batch_process(self):
        """停止批量处理"""
        if self.batch_thread and self.batch_thread.isRunning():
            self.batch_thread.stop()
            self.batch_thread.wait()
            
            # 隐藏图片列表面板的进度条
            self.image_list_panel.set_progress_visible(False)
            
            self.statusbar.showMessage("批量处理已停止")
    
    @pyqtSlot(int)
    def on_tab_changed(self, index: int):
        """标签页切换时记录最后活动的水印类型"""
        # 当用户切换到文本水印或图片水印标签页时，更新最后活动的水印类型
        if index == 0:
            self._last_active_watermark_type = 'text'
        elif index == 1:
            self._last_active_watermark_type = 'image'
    
    def on_quality_changed(self, value: int):
        """更新质量标签显示"""
        self.batch_quality_label.setText(f"{value}%")
    
    def on_batch_progress(self, progress: int, filename: str):
        """批量处理进度更新"""

        
        # 更新批量导出设置面板的进度显示
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在处理: {filename}")
    
    @pyqtSlot(dict)
    def on_batch_finished(self, results: dict):
        """批量导出处理完成"""
        # 更新UI状态
        self.start_batch_btn.setEnabled(True)
        self.stop_batch_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        

        
        image_paths = self.image_list_panel.get_image_paths()
        success_count = len(results)
        total_count = len(image_paths)
        
        if success_count > 0:
            self.statusbar.showMessage(f"批量处理完成! 成功: {success_count}/{total_count}")
            QMessageBox.information(self, "批量处理完成", 
                                  f"处理完成!\n成功: {success_count} 张\n失败: {total_count - success_count} 张\n\n输出目录: {self.output_directory}")
        else:
            self.statusbar.showMessage("批量处理完成，但没有成功处理的图片")
            QMessageBox.warning(self, "批量处理完成", "所有图片处理失败，请检查设置")
    
    @pyqtSlot(str)
    def on_batch_error(self, error_msg: str):
        """批量处理错误"""
        self.start_batch_btn.setEnabled(True)
        self.stop_batch_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        

        
        logger.error(f"批量处理错误: {error_msg}")
        QMessageBox.critical(self, "批量处理错误", f"处理过程中发生错误:\n{error_msg}")
    
    def clear_images(self):
        """清除所有图片"""
        image_paths = self.image_list_panel.get_image_paths()
        if image_paths:
            reply = QMessageBox.question(self, "清除图片", 
                                       f"确定要清除所有 {len(image_paths)} 张图片吗?")
            if reply == QMessageBox.StandardButton.Yes:
                self.image_list_panel.clear_images()
                self.current_image_path = None
                self.preview_panel.clear()
                self.update_image_count()
                self.statusbar.showMessage("已清除所有图片")
    
    def update_image_count(self):
        """更新图片计数"""
        count = len(self.image_paths)
        self.image_count_label.setText(f"图片: {count}")
    
    def save_settings(self):
        """保存模板 - 根据当前活动标签页只保存对应的水印类型设置"""
        try:
            # 获取当前活动标签页
            current_tab = self.settings_tabs.currentIndex()
            settings = {}
            
            # 根据当前活动标签页只保存对应的水印类型设置
            if current_tab == 0:  # 文本水印
                # 获取文本水印的设置
                text_settings = self.text_watermark_panel.get_settings()
                
                # 确保必要的字段存在并具有有效值
                if 'color' not in text_settings or not text_settings['color']:
                    text_settings['color'] = '#FFFFFF'  # 默认白色
                
                # 转换所有QColor对象为字符串表示
                from PyQt6.QtGui import QColor
                if isinstance(text_settings.get('color'), QColor):
                    text_settings['color'] = text_settings['color'].name()
                if isinstance(text_settings.get('bg_color'), QColor):
                    text_settings['bg_color'] = text_settings['bg_color'].name()
                
                settings['text_watermark'] = text_settings
                settings['watermark_type'] = 'text'  # 记录水印类型
            elif current_tab == 1:  # 图片水印
                # 获取图片水印的设置
                image_settings = self.image_watermark_panel.get_settings()
                settings['image_watermark'] = image_settings
                settings['watermark_type'] = 'image'  # 记录水印类型
            
            # 保存输出目录设置（如果有）
            if hasattr(self, 'output_directory') and self.output_directory:
                settings['output_directory'] = self.output_directory
            
            # 如果没有有效的水印设置，显示警告
            if not settings.get('text_watermark') and not settings.get('image_watermark'):
                QMessageBox.warning(self, "保存失败", "请切换到文本水印或图片水印标签页后再保存模板")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存模板", "", "配置文件 (*.json)"
            )
            
            if file_path:
                # 确保文件扩展名为.json
                if not file_path.endswith('.json'):
                    file_path += '.json'
                
                if self.config_manager.save_settings(settings, file_path):
                    self.statusbar.showMessage(f"{settings.get('watermark_type', '水印')}模板已保存到: {os.path.basename(file_path)}")
                else:
                    QMessageBox.warning(self, "保存失败", "无法保存模板文件")
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON序列化错误: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存模板时发生JSON错误: {str(e)}")
        except Exception as e:
            logger.error(f"保存模板失败: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存模板时发生错误: {str(e)}")
    
    def load_settings(self):
        """加载模板 - 根据模板中的水印类型应用对应的水印设置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "加载模板", "", "配置文件 (*.json)"
            )
            
            if file_path:
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "文件不存在", "指定的模板文件不存在")
                    return
                
                settings = self.config_manager.load_settings(file_path)
                
                # 获取模板中的水印类型（如果有）
                watermark_type = settings.get('watermark_type', '')
                
                # 根据模板中的内容决定应用哪种水印设置
                applied = False
                
                # 如果有明确的水印类型标记，优先使用
                if watermark_type == 'text' and 'text_watermark' in settings:
                    text_settings = settings['text_watermark']
                    # 确保必要的字段存在
                    if 'color' not in text_settings or not text_settings['color']:
                        text_settings['color'] = '#FFFFFF'
                    self.master_text_settings = text_settings
                    self.text_watermark_panel.set_settings(self.master_text_settings)
                    # 自动切换到文本水印标签页
                    self.settings_tabs.setCurrentIndex(0)
                    applied = True
                elif watermark_type == 'image' and 'image_watermark' in settings:
                    self.master_image_settings = settings['image_watermark']
                    self.image_watermark_panel.set_settings(self.master_image_settings)
                    # 自动切换到图片水印标签页
                    self.settings_tabs.setCurrentIndex(1)
                    applied = True
                # 兼容旧版模板（没有明确的水印类型标记）
                elif 'text_watermark' in settings and not applied:
                    text_settings = settings['text_watermark']
                    # 确保必要的字段存在
                    if 'color' not in text_settings or not text_settings['color']:
                        text_settings['color'] = '#FFFFFF'
                    self.master_text_settings = text_settings
                    self.text_watermark_panel.set_settings(self.master_text_settings)
                    # 自动切换到文本水印标签页
                    self.settings_tabs.setCurrentIndex(0)
                    applied = True
                elif 'image_watermark' in settings and not applied:
                    self.master_image_settings = settings['image_watermark']
                    self.image_watermark_panel.set_settings(self.master_image_settings)
                    # 自动切换到图片水印标签页
                    self.settings_tabs.setCurrentIndex(1)
                    applied = True
                
                # 设置输出目录
                if 'output_directory' in settings and settings['output_directory']:
                    self.output_directory = settings['output_directory']
                    self.output_path_label.setText(self.output_directory)
                
                if applied:
                    self.statusbar.showMessage(f"已加载模板: {os.path.basename(file_path)}")
                    # 如果当前有选中的图片，立即更新预览
                    if self.current_image_path:
                        self.preview_watermark()
                else:
                    QMessageBox.warning(self, "加载失败", "模板文件中没有有效的水印设置")
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            QMessageBox.critical(self, "加载失败", f"模板文件格式错误: {str(e)}")
        except Exception as e:
            logger.error(f"加载模板失败: {str(e)}")
            QMessageBox.critical(self, "加载失败", f"加载模板时发生错误: {str(e)}")
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>图片水印工具 - PhotoMark2</h2>
        <p>版本: 2.0</p>
        <p>一款功能强大的本地图片水印处理工具</p>
        <p>功能特性:</p>
        <ul>
        <li>支持文本和图片水印</li>
        <li>实时预览效果</li>
        <li>批量处理功能</li>
        <li>多种布局和效果选项</li>
        <li>保存/加载配置</li>
        </ul>
        <p>©2025 WuZilong 大模型辅助软件工程作业2</p>
        """
        
        QMessageBox.about(self, "关于 PhotoMark", about_text)
    
    def load_config(self):
        """加载默认配置"""
        try:
            default_settings = self.config_manager.load_default_settings()
            if default_settings:
                if 'text_watermark' in default_settings:
                    self.master_text_settings = default_settings['text_watermark']
                    self.text_watermark_panel.set_settings(self.master_text_settings)
                if 'image_watermark' in default_settings:
                    self.master_image_settings = default_settings['image_watermark']
                    self.image_watermark_panel.set_settings(self.master_image_settings)
        except Exception as e:
            logger.warning(f"加载默认配置失败: {str(e)}")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.batch_thread and self.batch_thread.isRunning():
            reply = QMessageBox.question(self, "确认退出", 
                                       "批量处理正在进行中，确定要退出吗?")
            if reply == QMessageBox.StandardButton.Yes:
                self.batch_thread.stop()
                self.batch_thread.wait(5000)  # 等待5秒
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoMarkApp()
    window.show()
    sys.exit(app.exec())