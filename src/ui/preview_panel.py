#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
预览面板组件
支持原图和带水印图片的对比显示，支持水印位置拖拽调整
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QSplitter, QSizePolicy,
                             QSlider, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QPainter, QMouseEvent, QPen, QColor


class DraggableWatermarkLabel(QLabel):
    """可拖拽的水印标签"""
    
    position_changed = pyqtSignal(QPoint)  # 水印位置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.watermark_pos = QPoint(50, 50)  # 默认水印位置
        self.watermark_size = QPoint(100, 50)  # 默认水印大小
        self.show_drag_handle = False
        
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在水印区域内
            watermark_rect = QRect(self.watermark_pos, self.watermark_size)
            if watermark_rect.contains(event.pos()):
                self.is_dragging = True
                self.drag_start_pos = event.pos()
                self.show_drag_handle = True
                self.update()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if self.is_dragging:
            # 计算拖拽偏移量
            delta = event.pos() - self.drag_start_pos
            self.watermark_pos += delta
            self.drag_start_pos = event.pos()
            
            # 限制水印位置在图片范围内
            if self.pixmap() and not self.pixmap().isNull():
                pixmap_size = self.pixmap().size()
                self.watermark_pos.setX(max(0, min(self.watermark_pos.x(), pixmap_size.width() - self.watermark_size.width())))
                self.watermark_pos.setY(max(0, min(self.watermark_pos.y(), pixmap_size.height() - self.watermark_size.height())))
            
            self.update()
            # 发送位置变化信号 - 确保发送的是实际图像坐标
            self.position_changed.emit(self.watermark_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.show_drag_handle = False
            self.update()
        
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)
        
        if self.show_drag_handle and self.pixmap() and not self.pixmap().isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制水印区域边框
            pen = QPen(QColor(255, 0, 0, 200), 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(QRect(self.watermark_pos, self.watermark_size))
            
            # 绘制拖拽手柄
            handle_rect = QRect(self.watermark_pos.x() + self.watermark_size.width() - 10,
                              self.watermark_pos.y() + self.watermark_size.height() - 10, 8, 8)
            painter.fillRect(handle_rect, QColor(255, 0, 0, 200))
    
    def set_watermark_position(self, pos: QPoint):
        """设置水印位置"""
        self.watermark_pos = pos
        self.update()
    
    def set_watermark_size(self, size: QPoint):
        """设置水印大小"""
        self.watermark_size = size
        self.update()
    
    def get_watermark_position(self) -> QPoint:
        """获取水印位置"""
        return self.watermark_pos
    
    def get_watermark_size(self) -> QPoint:
        """获取水印大小"""
        return self.watermark_size


class PreviewPanel(QWidget):
    """预览面板"""
    
    position_changed = pyqtSignal(QPoint)  # 水印位置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_watermark_position = QPoint(50, 50)  # 当前水印位置
        self.watermark_size = QPoint(100, 50)  # 水印大小
        self.original_pixmap = None
        self.watermarked_pixmap = None
        self.zoom_factor = 1.0  # 缩放系数，默认为100%
        self.zoom_levels = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]  # 预设缩放级别
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 水印预览区域（使用可拖拽标签）
        self.watermarked_scroll = QScrollArea()
        self.watermarked_label = DraggableWatermarkLabel()
        self.watermarked_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.watermarked_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.watermarked_scroll.setWidget(self.watermarked_label)
        self.watermarked_scroll.setWidgetResizable(True)
        
        # 连接水印位置改变信号
        self.watermarked_label.position_changed.connect(self.on_watermark_position_changed)
        
        # 添加水印预览区域
        layout.addWidget(self.watermarked_scroll)
        
        # 缩放控制区域
        zoom_layout = QHBoxLayout()
        
        # 缩放标签
        zoom_label = QLabel("缩放:")
        zoom_layout.addWidget(zoom_label)
        
        # 缩放滑块
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(0, len(self.zoom_levels) - 1)
        self.zoom_slider.setValue(3)  # 默认100%
        self.zoom_slider.setMinimumWidth(150)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        # 缩放百分比显示
        self.zoom_percent_label = QLabel("100%")
        self.zoom_percent_label.setMinimumWidth(50)
        self.zoom_percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_layout.addWidget(self.zoom_percent_label)
        
        # 缩放下拉框
        self.zoom_combo = QComboBox()
        for level in self.zoom_levels:
            self.zoom_combo.addItem(f"{int(level * 100)}%")
        self.zoom_combo.setCurrentIndex(3)  # 默认100%
        self.zoom_combo.currentIndexChanged.connect(self.on_zoom_combo_changed)
        zoom_layout.addWidget(self.zoom_combo)
        
        # 添加填充
        zoom_layout.addStretch()
        
        layout.addLayout(zoom_layout)
        
        # 信息显示区域
        self.info_label = QLabel("请选择一张图片开始预览")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.info_label)
    
    def set_image(self, image_path: str):
        """设置当前处理的图片"""
        try:
            self.original_pixmap = QPixmap(image_path)
            if not self.original_pixmap.isNull():
                # 更新信息
                filename = os.path.basename(image_path)
                size_info = f"{self.original_pixmap.width()}x{self.original_pixmap.height()}"
                self.info_label.setText(f"当前图片: {filename} ({size_info})")
                
                # 清空水印预览
                self.watermarked_label.setText("请预览水印效果")
                self.watermarked_pixmap = None
            else:
                self.info_label.setText("图片加载失败")
                
        except Exception as e:
            self.info_label.setText(f"加载错误: {str(e)}")
    
    def set_watermarked_image(self, pixmap: QPixmap):
        """设置带水印的图片"""
        try:
            self.watermarked_pixmap = pixmap
            if not self.watermarked_pixmap.isNull():
                # 应用当前缩放系数显示图片
                self.update_zoom_display()
                
                # 设置水印位置和大小
                self.watermarked_label.set_watermark_position(self.current_watermark_position)
                self.watermarked_label.set_watermark_size(self.watermark_size)
                
                # 更新信息
                if self.original_pixmap:
                    watermarked_size = f"{self.watermarked_pixmap.width()}x{self.watermarked_pixmap.height()}"
                    self.info_label.setText(f"水印预览 ({watermarked_size})")
                
                # 确保图片能够完整显示
                self.ensure_image_fully_visible()
            else:
                self.watermarked_label.setText("水印生成失败")
                
        except Exception as e:
            self.watermarked_label.setText("水印生成错误")
            self.info_label.setText(f"水印生成错误: {str(e)}")
    
    def clear(self):
        """清空预览"""
        self.watermarked_label.clear()
        self.watermarked_label.setText("请选择图片并预览水印效果")
        self.original_pixmap = None
        self.watermarked_pixmap = None
        self.info_label.setText("请选择一张图片开始预览")
    
    def get_original_pixmap(self) -> QPixmap:
        """获取原图"""
        return self.original_pixmap
    
    def get_watermarked_pixmap(self) -> QPixmap:
        """获取带水印的图片"""
        return self.watermarked_pixmap
    
    def on_watermark_position_changed(self, position: QPoint):
        """水印位置改变处理"""
        # 存储实际位置（考虑缩放因素）
        actual_position = QPoint(int(position.x() / self.zoom_factor), int(position.y() / self.zoom_factor))
        self.current_watermark_position = actual_position
        
        # 确保水印位置在图片范围内
        if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
            max_x = self.watermarked_pixmap.width() - int(self.watermark_size.x())
            max_y = self.watermarked_pixmap.height() - int(self.watermark_size.y())
            actual_position.setX(max(0, min(actual_position.x(), max_x)))
            actual_position.setY(max(0, min(actual_position.y(), max_y)))
            
        # 发送实际位置信号
        self.position_changed.emit(actual_position)
    
    def set_watermark_position(self, position: QPoint):
        """设置水印位置"""
        self.current_watermark_position = position
        if self.watermarked_label:
            self.watermarked_label.set_watermark_position(position)
    
    def set_watermark_size(self, size: QPoint):
        """设置水印大小"""
        self.watermark_size = size
        if self.watermarked_label:
            self.watermarked_label.set_watermark_size(size)
    
    def get_watermark_position(self) -> QPoint:
        """获取水印位置"""
        return self.current_watermark_position
    
    def get_watermark_size(self) -> QPoint:
        """获取水印大小"""
        return self.watermark_size
        
    def on_zoom_slider_changed(self, index):
        """缩放滑块变化处理"""
        if 0 <= index < len(self.zoom_levels):
            self.zoom_factor = self.zoom_levels[index]
            self.zoom_combo.setCurrentIndex(index)
            self.update_zoom_display()
            
    def on_zoom_combo_changed(self, index):
        """缩放下拉框变化处理"""
        if 0 <= index < len(self.zoom_levels):
            self.zoom_factor = self.zoom_levels[index]
            self.zoom_slider.setValue(index)
            self.update_zoom_display()
            
    def update_zoom_display(self):
        """更新缩放显示"""
        if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
            # 获取预览区域的实际可用尺寸
            scroll_area_size = self.watermarked_scroll.viewport().size()
            
            # 计算自适应缩放比例，确保图片完整显示
            if self.zoom_factor == 1.0:
                # 当缩放为100%时，检查图片是否超出预览区域
                pixmap_size = self.watermarked_pixmap.size()
                
                # 如果图片尺寸大于预览区域，则自动缩小以完整显示
                if pixmap_size.width() > scroll_area_size.width() or pixmap_size.height() > scroll_area_size.height():
                    # 计算合适的缩放比例
                    width_ratio = scroll_area_size.width() / pixmap_size.width()
                    height_ratio = scroll_area_size.height() / pixmap_size.height()
                    adaptive_ratio = min(width_ratio, height_ratio)
                    
                    # 使用自适应缩放
                    scaled_width = int(pixmap_size.width() * adaptive_ratio)
                    scaled_height = int(pixmap_size.height() * adaptive_ratio)
                    
                    scaled_pixmap = self.watermarked_pixmap.scaled(
                        scaled_width, scaled_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.watermarked_label.setPixmap(scaled_pixmap)
                else:
                    # 图片尺寸合适，直接显示原始图片
                    self.watermarked_label.setPixmap(self.watermarked_pixmap)
            else:
                # 对于其他缩放级别，使用缩放后的图片
                scaled_width = int(self.watermarked_pixmap.width() * self.zoom_factor)
                scaled_height = int(self.watermarked_pixmap.height() * self.zoom_factor)
                
                # 使用平滑缩放
                scaled_pixmap = self.watermarked_pixmap.scaled(
                    scaled_width, scaled_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # 更新显示
                self.watermarked_label.setPixmap(scaled_pixmap)
            
            self.watermarked_label.setText("")
            
            # 更新百分比标签
            self.zoom_percent_label.setText(f"{int(self.zoom_factor * 100)}%")
            
            # 更新水印大小以适应缩放
            scaled_watermark_width = int(self.watermark_size.x() * self.zoom_factor)
            scaled_watermark_height = int(self.watermark_size.y() * self.zoom_factor)
            self.watermarked_label.set_watermark_size(QPoint(scaled_watermark_width, scaled_watermark_height))
            
            # 更新水印位置以适应缩放
            scaled_watermark_x = int(self.current_watermark_position.x() * self.zoom_factor)
            scaled_watermark_y = int(self.current_watermark_position.y() * self.zoom_factor)
            self.watermarked_label.set_watermark_position(QPoint(scaled_watermark_x, scaled_watermark_y))
    
    def ensure_image_fully_visible(self):
        """确保图片能够完整显示在预览窗口中"""
        if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
            # 获取预览区域的实际可用尺寸
            scroll_area_size = self.watermarked_scroll.viewport().size()
            pixmap_size = self.watermarked_pixmap.size()
            
            # 如果图片尺寸大于预览区域，自动调整缩放级别
            if pixmap_size.width() > scroll_area_size.width() or pixmap_size.height() > scroll_area_size.height():
                # 计算合适的缩放比例
                width_ratio = scroll_area_size.width() / pixmap_size.width()
                height_ratio = scroll_area_size.height() / pixmap_size.height()
                adaptive_ratio = min(width_ratio, height_ratio)
                
                # 找到最接近的自适应缩放级别
                best_zoom_index = 3  # 默认100%
                best_zoom_diff = float('inf')
                
                for i, level in enumerate(self.zoom_levels):
                    diff = abs(level - adaptive_ratio)
                    if diff < best_zoom_diff:
                        best_zoom_diff = diff
                        best_zoom_index = i
                
                # 应用自适应缩放级别
                self.zoom_factor = self.zoom_levels[best_zoom_index]
                self.zoom_slider.setValue(best_zoom_index)
                self.zoom_combo.setCurrentIndex(best_zoom_index)
                
                # 更新显示
                self.update_zoom_display()