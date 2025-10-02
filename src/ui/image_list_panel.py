#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片列表面板
支持批量导入、缩略图显示和图片管理
"""

import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
                             QPushButton, QHBoxLayout, QFileDialog, QMessageBox,
                             QLabel, QProgressBar, QFrame, QGridLayout, QGroupBox)
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QMimeData
from PyQt6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent


class DragDropListWidget(QListWidget):
    """支持拖拽的列表控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否有图片文件
            urls = event.mimeData().urls()
            has_images = any(self.is_image_file(url.toLocalFile()) for url in urls)
            if has_images:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽释放事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            image_paths = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if self.is_image_file(file_path):
                    image_paths.append(file_path)
            
            if image_paths:
                # 发送信号通知父组件处理图片导入
                self.parent().handle_dropped_images(image_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def is_image_file(self, file_path):
        """检查文件是否为支持的图片格式"""
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
        return any(file_path.lower().endswith(ext) for ext in valid_extensions)


class ImageListPanel(QWidget):
    """图片列表面板"""
    
    # 图片选中信号
    image_selected = pyqtSignal(str)
    # 图片列表改变信号
    image_list_changed = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.image_paths = []  # 存储图片路径
        self.logger = logging.getLogger(__name__)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题和统计信息
        header_layout = QHBoxLayout()
        self.title_label = QLabel("图片列表")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)
        
        self.count_label = QLabel("0 张图片")
        self.count_label.setStyleSheet("color: #666;")
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        layout.addLayout(header_layout)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # 图片列表
        self.image_list = DragDropListWidget()
        self.image_list.setIconSize(QSize(120, 120))  # 设置图标大小
        self.image_list.setSpacing(8)  # 设置间距
        self.image_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.image_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.image_list)
        
        # 进度条（用于批量操作）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮布局
        button_group = QGroupBox("操作")
        button_layout = QGridLayout(button_group)
        
        self.import_btn = QPushButton("导入图片")
        self.import_btn.clicked.connect(self.import_images)
        button_layout.addWidget(self.import_btn, 0, 0)
        
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        button_layout.addWidget(self.add_folder_btn, 0, 1)
        
        self.remove_btn = QPushButton("移除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_btn, 1, 0)
        
        self.clear_btn = QPushButton("清除列表")
        self.clear_btn.clicked.connect(self.clear_images)
        button_layout.addWidget(self.clear_btn, 1, 1)
        
        layout.addWidget(button_group)
        
    def add_images(self, image_paths):
        """添加图片到列表"""
        valid_images = []
        
        for image_path in image_paths:
            if image_path not in self.image_paths:
                # 验证图片文件
                if not os.path.exists(image_path):
                    self.logger.warning(f"文件不存在: {image_path}")
                    continue
                    
                if not self.is_valid_image(image_path):
                    self.logger.warning(f"不支持的图片格式: {image_path}")
                    continue
                
                self.image_paths.append(image_path)
                valid_images.append(image_path)
                
                # 创建列表项
                item = QListWidgetItem()
                item.setText(os.path.basename(image_path))
                item.setToolTip(image_path)
                item.setData(Qt.ItemDataRole.UserRole, image_path)  # 将路径存储在用户数据中
                
                # 加载缩略图
                try:
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        # 缩放缩略图
                        scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, 
                                                    Qt.TransformationMode.SmoothTransformation)
                        item.setIcon(QIcon(scaled_pixmap))
                    else:
                        self.logger.warning(f"无法加载图片: {image_path}")
                except Exception as e:
                    self.logger.error(f"加载缩略图失败: {image_path}, 错误: {e}")
                
                self.image_list.addItem(item)
        
        if valid_images:
            self.update_count()
            self.image_list_changed.emit(self.image_paths)
            
            # 如果这是第一张图片，自动选中
            if self.image_list.count() > 0 and self.image_list.currentRow() == -1:
                self.image_list.setCurrentRow(0)
                self.image_selected.emit(self.image_paths[0])
    
    def handle_dropped_images(self, image_paths):
        """处理拖拽导入的图片"""
        self.add_images(image_paths)
            
    def import_images(self):
        """导入图片"""
        try:
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif);;所有文件 (*)")
            
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    self.add_images(selected_files)
                    QMessageBox.information(self, "导入成功", f"成功导入 {len(selected_files)} 张图片")
        except Exception as e:
            self.logger.error(f"导入图片失败: {str(e)}")
            QMessageBox.critical(self, "导入错误", f"导入图片时发生错误:\n{str(e)}")
    
    def add_folder(self):
        """添加文件夹中的所有图片"""
        try:
            folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
            if folder_path:
                image_files = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if self.is_valid_image_file(file):
                            image_files.append(os.path.join(root, file))
                
                if image_files:
                    self.add_images(image_files)
                    QMessageBox.information(self, "添加成功", f"从文件夹添加 {len(image_files)} 张图片")
                else:
                    QMessageBox.warning(self, "无图片文件", "所选文件夹中没有找到支持的图片文件")
        except Exception as e:
            self.logger.error(f"添加文件夹失败: {str(e)}")
            QMessageBox.critical(self, "添加错误", f"添加文件夹时发生错误:\n{str(e)}")
            
    def on_item_clicked(self, item):
        """列表项被点击"""
        image_path = item.data(Qt.ItemDataRole.UserRole)
        if image_path:
            self.image_selected.emit(image_path)
    
    def remove_selected(self):
        """移除选中的图片"""
        current_row = self.image_list.currentRow()
        if current_row >= 0:
            item = self.image_list.takeItem(current_row)
            image_path = item.data(1)
            self.image_paths.remove(image_path)
            self.update_count()
            self.image_list_changed.emit(self.image_paths)
    
    def clear_images(self):
        """清除所有图片"""
        if self.image_paths:
            reply = QMessageBox.question(self, "确认清除", "确定要清除所有图片吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.image_list.clear()
                self.image_paths.clear()
                self.update_count()
                self.image_list_changed.emit(self.image_paths)
    
    def update_count(self):
        """更新图片数量显示"""
        count = len(self.image_paths)
        self.count_label.setText(f"{count} 张图片")
    
    def is_valid_image_file(self, filename):
        """检查文件是否为支持的图片格式"""
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
        return any(filename.lower().endswith(ext) for ext in valid_extensions)
    
    def is_valid_image(self, filepath):
        """验证图片文件是否有效"""
        try:
            # 检查文件扩展名
            if not self.is_valid_image_file(filepath):
                return False
            
            # 尝试加载图片
            pixmap = QPixmap(filepath)
            return not pixmap.isNull()
            
        except Exception:
            return False
    
    def get_image_paths(self):
        """获取所有图片路径"""
        return self.image_paths.copy()
    
    def get_selected_image_path(self):
        """获取当前选中的图片路径"""
        current_row = self.image_list.currentRow()
        if current_row >= 0 and current_row < len(self.image_paths):
            return self.image_paths[current_row]
        return None
    
    def set_progress_visible(self, visible):
        """设置进度条可见性"""
        self.progress_bar.setVisible(visible)
    
    def set_progress_value(self, value):
        """设置进度条值"""
        self.progress_bar.setValue(value)
    
    def set_progress_range(self, minimum, maximum):
        """设置进度条范围"""
        self.progress_bar.setMinimum(minimum)
        self.progress_bar.setMaximum(maximum)