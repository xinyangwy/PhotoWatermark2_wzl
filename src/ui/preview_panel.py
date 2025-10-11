#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
预览面板组件
支持原图和带水印图片的对比显示，支持水印位置拖拽调整
"""

import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QSizePolicy, QToolTip)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QPainter, QMouseEvent, QPen, QColor, QCursor

# 配置日志
logger = logging.getLogger(__name__)


class DraggableWatermarkLabel(QLabel):
    """可拖拽的水印标签"""
    
    position_changed = pyqtSignal(QPoint)  # 水印位置改变信号
    drag_started = pyqtSignal()  # 拖拽开始信号
    drag_finished = pyqtSignal()  # 拖拽结束信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.watermark_pos = QPoint(50, 50)  # 默认水印位置
        self.watermark_size = QPoint(0, 0)  # 动态计算水印大小
        self.is_dragging = False  # 拖拽状态标记
        self.drag_start_pos = QPoint()  # 拖拽起始位置
        self.watermark_rect = QRect()  # 水印区域
        # 启用鼠标跟踪以支持拖拽功能
        self.setMouseTracking(True)
        
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件 - 开始拖拽"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查点击位置是否在水印区域内
            if self.watermark_size.x() > 0 and self.watermark_size.y() > 0:
                watermark_rect = QRect(self.watermark_pos, self.watermark_size)
                if watermark_rect.contains(event.position().toPoint()):
                    self.is_dragging = True
                    self.drag_start_pos = event.position().toPoint() - self.watermark_pos
                    self.drag_started.emit()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    logger.debug(f"开始拖拽水印，位置: {self.watermark_pos}, 大小: {self.watermark_size}")
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """鼠标进入水印区域时显示提示"""
        if self.pixmap() and not self.pixmap().isNull():
            # 检查鼠标位置是否在水印区域内
            watermark_rect = QRect(self.watermark_pos, self.watermark_size)
            current_pos = self.mapFromGlobal(QCursor.pos())
            if watermark_rect.contains(current_pos):
                QToolTip.showText(QCursor.pos(), "拖拽以移动水印位置")
        super().enterEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件 - 处理拖拽"""
        if self.is_dragging:
            # 计算新位置
            new_pos = event.position().toPoint() - self.drag_start_pos
            self.update_position(new_pos)
            logger.debug(f"拖拽中，新位置: {new_pos}")
        else:
            # 悬停在水印上时显示手型光标
            if self.pixmap() and not self.pixmap().isNull() and self.watermark_size.x() > 0 and self.watermark_size.y() > 0:
                watermark_rect = QRect(self.watermark_pos, self.watermark_size)
                if watermark_rect.contains(event.position().toPoint()):
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                else:
                    self.unsetCursor()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件 - 结束拖拽"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.drag_finished.emit()
            self.unsetCursor()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """绘制事件 - 显示水印可拖拽区域"""
        super().paintEvent(event)
        
        # 只在有水印图片且水印大小有效时绘制水印区域边框
        if self.pixmap() and not self.pixmap().isNull() and self.watermark_size.x() > 0 and self.watermark_size.y() > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制水印区域边框（红色虚线，便于用户识别可拖拽区域）
            border_pen = QPen(QColor(255, 0, 0, 180), 2)
            border_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
            watermark_rect = QRect(self.watermark_pos, self.watermark_size)
            painter.drawRect(watermark_rect)
            
            # 在边框内添加提示文字
            painter.setPen(QPen(QColor(255, 255, 255, 200)))
            painter.drawText(watermark_rect, Qt.AlignmentFlag.AlignCenter, "可拖拽")
    
    def set_watermark_position(self, pos: QPoint):
        """设置水印位置"""
        self.watermark_pos = pos
        self.ensure_valid_position()
        self.update()
    
    def set_watermark_size(self, size: QPoint):
        """设置水印大小"""
        self.watermark_size = size
        self.watermark_rect = QRect(self.watermark_pos, self.watermark_size)
        self.ensure_valid_position()
        self.update()
        logger.debug(f"水印大小已设置: {self.watermark_size}")
    
    def get_watermark_position(self) -> QPoint:
        """获取水印位置"""
        return self.watermark_pos
    
    def get_watermark_size(self) -> QPoint:
        """获取水印大小"""
        return self.watermark_size
        
    def ensure_valid_position(self):
        """确保水印位置在有效范围内 - 简化版，移除吸附功能"""
        if self.pixmap() and not self.pixmap().isNull():
            pixmap_size = self.pixmap().size()
            
            wm_width, wm_height = self.watermark_size.x(), self.watermark_size.y()
            img_width, img_height = pixmap_size.width(), pixmap_size.height()
            
            # 计算最大允许位置
            max_x = img_width - wm_width
            max_y = img_height - wm_height
            
            # 确保水印完全在图片范围内
            self.watermark_pos.setX(max(0, min(self.watermark_pos.x(), max_x)))
            self.watermark_pos.setY(max(0, min(self.watermark_pos.y(), max_y)))
            
            logger.debug(f"水印位置已调整: {self.watermark_pos}, 图片尺寸: {img_width}x{img_height}")
            
    def update_position(self, pos: QPoint):
        """更新水印位置并发射信号"""
        self.watermark_pos = pos
        self.ensure_valid_position()
        self.update()
        # 发射位置改变信号
        self.position_changed.emit(self.watermark_pos)





class PreviewPanel(QWidget):
    """预览面板"""
    
    # 定义信号
    watermark_position_changed = pyqtSignal(QPoint)  # 水印位置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_watermark_position = QPoint(50, 50)  # 当前水印位置
        self.watermark_size = QPoint(100, 50)  # 水印大小
        self.original_pixmap = None
        self.watermarked_pixmap = None
        self.zoom_factor = 1.0  # 缩放系数，默认为100%且固定不变
        self.init_ui()
        
        # 连接信号
        self._connect_signals()
        
    def _connect_signals(self):
        """连接信号和槽函数"""
        # 连接水印位置改变信号到槽函数
        self.watermarked_label.position_changed.connect(self.on_watermark_position_changed)
        self.watermarked_label.drag_started.connect(self.on_drag_started)
        self.watermarked_label.drag_finished.connect(self.on_drag_finished)
        
    def on_watermark_position_changed(self, pos: QPoint):
        """处理水印位置改变事件"""
        self.current_watermark_position = pos
        # 发射水印位置改变信号
        self.watermark_position_changed.emit(pos)
        logger.debug(f"水印位置已更改: {pos.x()}, {pos.y()}")
        
    def on_drag_started(self):
        """处理拖拽开始事件"""
        logger.debug("水印拖拽开始")
        # 可以在这里添加拖拽开始时的处理逻辑，如显示提示信息等
    
    def on_drag_finished(self):
        """处理拖拽结束事件"""
        logger.debug("水印拖拽结束")
        # 可以在这里添加拖拽结束时的处理逻辑，如保存设置等
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 水印预览区域（使用可拖拽的水印标签）
        self.watermarked_scroll = QScrollArea()
        self.watermarked_label = DraggableWatermarkLabel()
        self.watermarked_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.watermarked_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.watermarked_scroll.setWidget(self.watermarked_label)
        self.watermarked_scroll.setWidgetResizable(True)
        
        # 添加水印预览区域
        layout.addWidget(self.watermarked_scroll)
        
        # 缩放显示（固定为100%，不允许调整）
        zoom_info_layout = QHBoxLayout()
        zoom_info_label = QLabel("缩放: 100%")
        zoom_info_layout.addWidget(zoom_info_label)
        zoom_info_layout.addStretch()
        layout.addLayout(zoom_info_layout)
        
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
                logger.warning(f"图片加载失败: {image_path}")
                
        except Exception as e:
            self.info_label.setText(f"加载错误: {str(e)}")
            logger.error(f"图片加载错误: {str(e)}", exc_info=True)
    
    def set_watermarked_image(self, pixmap: QPixmap):
        """设置带水印的图片"""
        try:
            self.watermarked_pixmap = pixmap
            if not self.watermarked_pixmap.isNull():
                # 应用当前缩放系数显示图片
                self.update_zoom_display()
                
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
            # 记录错误到日志
            logger.error(f"水印生成错误: {str(e)}")
    
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
    
    def set_watermark_position(self, position: QPoint):
        """设置水印位置"""
        self.watermark_position = position
        if self.preview_label:
            self.preview_label.set_watermark_position(position)
            logger.debug(f"预览面板设置水印位置: {position.x()}, {position.y()}")
        
    def set_watermark_size(self, size: QPoint):
        """设置水印大小"""
        self.watermark_size = size
        if self.preview_label:
            self.preview_label.set_watermark_size(size)
            logger.debug(f"预览面板设置水印大小: {size.x()}x{size.y()}")
    
    def get_watermark_position(self) -> QPoint:
        """获取水印位置"""
        return self.current_watermark_position
    
    def get_watermark_size(self) -> QPoint:
        """获取水印大小"""
        return self.watermark_size
        
    def update_zoom_display(self):
        """更新缩放显示"""
        try:
            if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
                # 获取预览区域的实际可用尺寸
                scroll_area_size = self.watermarked_scroll.viewport().size()
                
                # 获取图片尺寸
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
                
                self.watermarked_label.setText("")
                
            # 记录日志
            if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
                img_width = self.watermarked_pixmap.width()
                img_height = self.watermarked_pixmap.height()
                if img_width > 0 and img_height > 0:
                    display_width = int(img_width * self.zoom_factor)
                    display_height = int(img_height * self.zoom_factor)
                    logger.debug(f"缩放已更新: {self.zoom_factor}, 显示尺寸: {display_width}x{display_height}")
                    
        except Exception as e:
            logger.error(f"更新缩放显示时出错: {str(e)}")

    def ensure_image_fully_visible(self):
        """确保图片能够完整显示在预览窗口中 - 固定使用100%缩放"""
        if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
            # 直接调用update_zoom_display来确保图片正确显示（会自动适应窗口大小）
            self.update_zoom_display()