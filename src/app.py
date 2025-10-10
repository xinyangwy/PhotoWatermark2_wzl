#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片水印工具主应用
提供现代化的GUI界面，支持批量处理和实时预览
"""

import sys
import os
import logging
from typing import List, Dict, Any
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QFileDialog, QMessageBox,
                             QMenuBar, QMenu, QStatusBar, QToolBar, QTabWidget,
                             QProgressBar, QLabel, QPushButton, QFrame, QScrollArea)
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
                    
                    # 尝试加载图片验证有效性
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        valid_images.append(image_path)
                    else:
                        logger.warning(f"无法加载图片: {image_path}")
                        
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
                        output_filename = f"{os.path.splitext(filename)[0]}_watermarked{os.path.splitext(filename)[1]}"
                        output_path = os.path.join(self.output_dir, output_filename)
                        result_pixmap.save(output_path)
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
        
        # 连接拖拽位置信号
        self.preview_panel.position_changed.connect(self.on_watermark_position_changed)
    
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
        
        # 批量设置标签页
        self.batch_panel = self.create_batch_panel()
        self.settings_tabs.addTab(self.batch_panel, "批量设置")
    
    def create_batch_panel(self) -> QWidget:
        """创建批量设置面板"""
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
        
        self.start_batch_btn = QPushButton("开始批量处理")
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
        settings_menu = menubar.addMenu('设置')
        
        save_settings_action = QAction('保存设置', self)
        save_settings_action.triggered.connect(self.save_settings)
        settings_menu.addAction(save_settings_action)
        
        load_settings_action = QAction('加载设置', self)
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
        
        # 预览面板拖拽位置信号
        self.preview_panel.position_changed.connect(self.on_watermark_position_changed)
    
    @pyqtSlot(str)
    def on_image_selected(self, image_path: str):
        """图片被选中"""
        self.current_image_path = image_path
        self.preview_panel.set_image(image_path)
        self.statusbar.showMessage(f"已选择图片: {os.path.basename(image_path)}")
        self.preview_watermark()
    
    @pyqtSlot(list)
    def on_image_list_changed(self, image_paths: list):
        """图片列表改变"""
        self.image_paths = image_paths
        self.update_image_count()
    
    @pyqtSlot()
    def on_settings_changed(self):
        """水印设置改变"""
        if self.current_image_path:
            self.preview_watermark()
            
        # 检查是否需要应用到所有图片
        current_tab = self.settings_tabs.currentIndex()
        if current_tab == 0:  # 文本水印
            settings = self.text_watermark_panel.get_settings()
            if settings.get('apply_to_all', False) and self.image_paths:
                # 这里不需要立即处理所有图片，只需要将设置保存
                # 实际的批量处理将在用户点击批量处理按钮时进行
                pass
        elif current_tab == 1:  # 图片水印
            settings = self.image_watermark_panel.get_settings()
            if settings.get('apply_to_all', False) and self.image_paths:
                # 同样，这里只需要保存设置
                pass
    
    @pyqtSlot(QPoint)
    def on_watermark_position_changed(self, position: QPoint):
        """水印位置拖拽改变"""
        # 获取当前活动的水印面板
        current_tab = self.settings_tabs.currentIndex()
        
        # 根据当前选择的水印类型更新相应面板
        if current_tab == 0:  # 文本水印
            self.text_watermark_panel.update_position_from_drag(position.x(), position.y())
        else:  # 图片水印
            self.image_watermark_panel.update_position_from_drag(position.x(), position.y())
            
        # 立即刷新预览
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
    
    def start_async_import(self, image_paths: List[str], operation_name: str):
        """开始异步导入"""
        # 停止之前的导入线程
        if self.import_thread and self.import_thread.isRunning():
            self.import_thread.stop()
            self.import_thread.wait()
        
        # 显示进度条
        self.image_list_panel.set_progress_visible(True)
        self.image_list_panel.set_progress_range(0, len(image_paths))
        self.image_list_panel.set_progress_value(0)
        
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
        # 更新图片列表面板的进度条
        image_paths = self.import_thread.image_paths if self.import_thread else []
        if image_paths:
            current_progress = int((progress / 100) * len(image_paths))
            self.image_list_panel.set_progress_value(current_progress)
        
        # 更新状态栏
        total_count = len(image_paths) if image_paths else 0
        current_count = int((progress / 100) * total_count) if total_count > 0 else 0
        self.statusbar.showMessage(f"导入中... ({current_count}/{total_count}) - {filename}")
    
    @pyqtSlot(list)
    def on_import_finished(self, valid_images: List[str]):
        """导入完成"""
        # 隐藏进度条
        self.image_list_panel.set_progress_visible(False)
        
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
        # 隐藏进度条
        self.image_list_panel.set_progress_visible(False)
        
        logger.error(f"导入错误: {error_msg}")
        QMessageBox.critical(self, "导入错误", f"导入过程中发生错误:\n{error_msg}")
        self.statusbar.showMessage("导入失败")
    
    def preview_watermark(self):
        """预览水印效果"""
        if not self.current_image_path:
            QMessageBox.information(self, "预览", "请先选择一张图片")
            return
        
        current_tab = self.settings_tabs.currentIndex()
        
        try:
            if current_tab == 0:  # 文本水印
                settings = self.text_watermark_panel.get_settings()
                # 预览模式下设置较低的日志级别，避免过多日志
                settings['log_level'] = 'debug'
                result_pixmap = self.watermark_processor.add_text_watermark(
                    self.current_image_path, settings.get('text', ''), settings)
            elif current_tab == 1:  # 图片水印
                settings = self.image_watermark_panel.get_settings()
                watermark_path = settings.get('watermark_path', '')
                if not watermark_path or not os.path.exists(watermark_path):
                    QMessageBox.warning(self, "预览失败", "请先选择有效的水印图片")
                    return
                # 预览模式下设置较低的日志级别，避免过多日志
                settings['log_level'] = 'debug'
                result_pixmap = self.watermark_processor.add_image_watermark(
                    self.current_image_path, watermark_path, settings)
            else:
                return
            
            if result_pixmap and not result_pixmap.isNull():
                self.preview_panel.set_watermarked_image(result_pixmap)
                self.statusbar.showMessage("水印预览已更新")
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
        """开始批量处理"""
        image_paths = self.image_list_panel.get_image_paths()
        if not image_paths:
            QMessageBox.information(self, "批量处理", "没有图片需要处理")
            return
        
        if not hasattr(self, 'output_directory') or not self.output_directory:
            QMessageBox.warning(self, "批量处理", "请先选择输出目录")
            return
        
        # 获取当前设置
        current_tab = self.settings_tabs.currentIndex()
        if current_tab == 0:  # 文本水印
            settings = self.text_watermark_panel.get_settings()
            watermark_type = 'text'
        elif current_tab == 1:  # 图片水印
            settings = self.image_watermark_panel.get_settings()
            watermark_path = settings.get('watermark_path', '')
            if not watermark_path or not os.path.exists(watermark_path):
                QMessageBox.warning(self, "批量处理", "请先选择有效的水印图片")
                return
            watermark_type = 'image'
        else:
            QMessageBox.warning(self, "批量处理", "请先配置水印设置")
            return
        
        # 检查是否需要应用到所有图片的设置（虽然在批量处理中这是默认行为，但我们保留这个检查以保持一致性）
        if settings.get('apply_to_all', False):
            # 记录日志，表明正在使用应用到所有图片的设置
            logger.info(f"开始批量处理 {len(image_paths)} 张图片，使用应用到所有图片的设置")
        
        # 设置进度条
        self.image_list_panel.set_progress_visible(True)
        self.image_list_panel.set_progress_range(0, len(image_paths))
        self.image_list_panel.set_progress_value(0)
        
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
    
    @pyqtSlot(int, str)
    def on_batch_progress(self, progress: int, filename: str):
        """批量处理进度更新"""
        # 更新图片列表面板的进度条
        image_paths = self.image_list_panel.get_image_paths()
        if image_paths:
            current_progress = int((progress / 100) * len(image_paths))
            self.image_list_panel.set_progress_value(current_progress)
        
        # 更新批量设置面板的进度显示
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在处理: {filename}")
    
    @pyqtSlot(dict)
    def on_batch_finished(self, results: dict):
        """批量处理完成"""
        # 更新UI状态
        self.start_batch_btn.setEnabled(True)
        self.stop_batch_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # 隐藏图片列表面板的进度条
        self.image_list_panel.set_progress_visible(False)
        
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
        
        # 隐藏图片列表面板的进度条
        self.image_list_panel.set_progress_visible(False)
        
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
        """保存设置"""
        try:
            settings = {
                'text_watermark': self.text_watermark_panel.get_settings(),
                'image_watermark': self.image_watermark_panel.get_settings(),
                'output_directory': getattr(self, 'output_directory', '')
            }
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存设置", "", "配置文件 (*.json)"
            )
            
            if file_path:
                self.config_manager.save_settings(settings, file_path)
                self.statusbar.showMessage("设置已保存")
                
        except Exception as e:
            logger.error(f"保存设置失败: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存设置时发生错误: {str(e)}")
    
    def load_settings(self):
        """加载设置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "加载设置", "", "配置文件 (*.json)"
            )
            
            if file_path:
                settings = self.config_manager.load_settings(file_path)
                
                if 'text_watermark' in settings:
                    self.text_watermark_panel.set_settings(settings['text_watermark'])
                if 'image_watermark' in settings:
                    self.image_watermark_panel.set_settings(settings['image_watermark'])
                if 'output_directory' in settings:
                    self.output_directory = settings['output_directory']
                    self.output_path_label.setText(self.output_directory)
                
                self.statusbar.showMessage("设置已加载")
                
        except Exception as e:
            logger.error(f"加载设置失败: {str(e)}")
            QMessageBox.critical(self, "加载失败", f"加载设置时发生错误: {str(e)}")
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>图片水印工具 - PhotoMark</h2>
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
        <p>© 2024 PhotoMark Team</p>
        """
        
        QMessageBox.about(self, "关于 PhotoMark", about_text)
    
    def load_config(self):
        """加载配置"""
        try:
            # 尝试加载默认配置
            default_settings = self.config_manager.load_default_settings()
            if default_settings:
                if 'text_watermark' in default_settings:
                    self.text_watermark_panel.set_settings(default_settings['text_watermark'])
                if 'image_watermark' in default_settings:
                    self.image_watermark_panel.set_settings(default_settings['image_watermark'])
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
