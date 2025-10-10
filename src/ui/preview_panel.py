#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
预览面板组件
支持原图和带水印图片的对比显示，支持水印位置拖拽调整
"""

import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QSplitter, QSizePolicy,
                             QSlider, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QPainter, QMouseEvent, QPen, QColor

# 配置日志
logger = logging.getLogger(__name__)


class DraggableWatermarkLabel(QLabel):
    """可拖拽的水印标签"""
    
    position_changed = pyqtSignal(QPoint)  # 水印位置改变信号
    drag_started = pyqtSignal()  # 开始拖拽
    drag_finished = pyqtSignal()  # 结束拖拽
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.watermark_pos = QPoint(50, 50)  # 默认水印位置
        self.watermark_size = QPoint(100, 50)  # 默认水印大小
        self.show_drag_handle = False
        self.show_grid = False  # 显示对齐网格
        self.snap_enabled = True  # 启用吸附功能
        self.snap_distance = 10  # 吸附距离（像素）
        self.last_update_pos = QPoint()  # 上次更新位置
        self.update_interval = 5  # 更新间隔（像素），减少重绘频率
        self.setMouseTracking(True)  # 启用鼠标跟踪，提高交互体验
        
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在水印区域内
            watermark_rect = QRect(self.watermark_pos, self.watermark_size)
            # 增加可点击区域，使水印更容易被选中
            extended_rect = watermark_rect.adjusted(-10, -10, 10, 10)
            if extended_rect.contains(event.pos()):
                self.is_dragging = True
                self.drag_start_pos = event.pos()
                self.show_drag_handle = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)  # 鼠标变为抓手形状
                self.drag_started.emit()
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
            self.ensure_valid_position()
            
            # 节流更新机制 - 只有当位置变化超过阈值时才更新
            if (abs(self.watermark_pos.x() - self.last_update_pos.x()) >= self.update_interval or 
                abs(self.watermark_pos.y() - self.last_update_pos.y()) >= self.update_interval):
                
                # 强制重绘以提供视觉反馈
                self.update()
                
                # 发送位置变化信号 - 确保发送的是实际图像坐标
                self.position_changed.emit(self.watermark_pos)
                
                # 更新上次更新位置
                self.last_update_pos = QPoint(self.watermark_pos)
        else:
            # 鼠标悬停在水印区域上时改变鼠标形状
            # 优化：减少不必要的矩形计算
            watermark_rect = QRect(self.watermark_pos, self.watermark_size)
            # 增加更大的可点击区域，使水印更容易被选中
            extended_rect = watermark_rect.adjusted(-15, -15, 15, 15)
            
            # 只在需要时才更新网格显示和鼠标形状
            if extended_rect.contains(event.pos()):
                if self.cursor() != Qt.CursorShape.OpenHandCursor:
                    self.setCursor(Qt.CursorShape.OpenHandCursor)  # 鼠标变为张开的手形
                # 显示网格辅助对齐
                if not self.show_grid:
                    self.show_grid = True
                    self.update()
            else:
                if self.cursor() != Qt.CursorShape.ArrowCursor:
                    self.unsetCursor()  # 恢复默认鼠标形状
                # 隐藏网格
                if self.show_grid:
                    self.show_grid = False
                    self.update()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.show_drag_handle = False
            self.unsetCursor()  # 恢复默认鼠标形状
            self.drag_finished.emit()
            self.update()
            # 确保最后一次位置被正确发送
            self.position_changed.emit(self.watermark_pos)
        
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """绘制事件 - 优化版，减少不必要的绘制操作"""
        super().paintEvent(event)
        
        # 只在需要绘制额外元素时才创建painter对象
        if (self.show_drag_handle or self.show_grid) and self.pixmap() and not self.pixmap().isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 计算中心点（只计算一次）
            center_x = self.watermark_pos.x() + self.watermark_size.x() // 2
            center_y = self.watermark_pos.y() + self.watermark_size.y() // 2
            
            # 绘制对齐网格（如果启用且非拖拽状态）
            if self.show_grid and not self.is_dragging:
                # 减少透明度以降低绘制开销
                grid_pen = QPen(QColor(200, 200, 200, 80), 1)
                grid_pen.setStyle(Qt.PenStyle.DotLine)
                painter.setPen(grid_pen)
                
                # 绘制中心参考线
                pixmap_size = self.pixmap().size()
                center_pix_x = pixmap_size.width() // 2
                center_pix_y = pixmap_size.height() // 2
                
                painter.drawLine(center_pix_x, 0, center_pix_x, pixmap_size.height())
                painter.drawLine(0, center_pix_y, pixmap_size.width(), center_pix_y)
            
            # 绘制水印区域边框
            border_pen = QPen(QColor(255, 0, 0, 220), 2)
            border_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
            painter.drawRect(QRect(self.watermark_pos, self.watermark_size))
            
            # 绘制拖拽手柄
            handle_rect = QRect(self.watermark_pos.x() + self.watermark_size.x() - 12,
                              self.watermark_pos.y() + self.watermark_size.y() - 12, 10, 10)
            painter.fillRect(handle_rect, QColor(255, 0, 0, 220))
            
            # 绘制中心点标记
            center_pen = QPen(QColor(255, 255, 0, 220), 2)
            painter.setPen(center_pen)
            painter.drawLine(center_x - 5, center_y, center_x + 5, center_y)
            painter.drawLine(center_x, center_y - 5, center_x, center_y + 5)
            
            # 绘制对齐辅助线（只在拖拽时）
            if self.is_dragging:
                # 降低透明度以提高性能
                align_pen = QPen(QColor(0, 255, 0, 120), 1)
                align_pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(align_pen)
                
                # 水平对齐线
                painter.drawLine(0, center_y, self.width(), center_y)
                # 垂直对齐线
                painter.drawLine(center_x, 0, center_x, self.height())
    
    def set_watermark_position(self, pos: QPoint):
        """设置水印位置"""
        self.watermark_pos = pos
        self.ensure_valid_position()
        self.update()
    
    def set_watermark_size(self, size: QPoint):
        """设置水印大小"""
        self.watermark_size = size
        self.ensure_valid_position()
        self.update()
    
    def get_watermark_position(self) -> QPoint:
        """获取水印位置"""
        return self.watermark_pos
    
    def get_watermark_size(self) -> QPoint:
        """获取水印大小"""
        return self.watermark_size
        
    def ensure_valid_position(self):
        """确保水印位置在有效范围内 - 优化版，减少计算复杂度"""
        if self.pixmap() and not self.pixmap().isNull():
            pixmap_size = self.pixmap().size()
            
            # 缓存常用计算结果
            snap_dist = self.snap_distance
            wm_pos_x, wm_pos_y = self.watermark_pos.x(), self.watermark_pos.y()
            wm_width, wm_height = self.watermark_size.x(), self.watermark_size.y()
            img_width, img_height = pixmap_size.width(), pixmap_size.height()
            
            # 计算最大允许位置（只计算一次）
            max_x = img_width - wm_width
            max_y = img_height - wm_height
            
            # 应用网格对齐和吸附功能
            if self.snap_enabled:
                # 对齐到图片边界（优化条件判断）
                if wm_pos_x <= snap_dist:
                    self.watermark_pos.setX(0)
                elif (max_x - wm_pos_x) <= snap_dist:
                    self.watermark_pos.setX(max_x)
                else:
                    # 仅在未吸附到边界时计算中心线吸附
                    center_x = (img_width - wm_width) // 2
                    if abs(wm_pos_x - center_x) <= snap_dist:
                        self.watermark_pos.setX(center_x)
                
                if wm_pos_y <= snap_dist:
                    self.watermark_pos.setY(0)
                elif (max_y - wm_pos_y) <= snap_dist:
                    self.watermark_pos.setY(max_y)
                else:
                    # 仅在未吸附到边界时计算中心线吸附
                    center_y = (img_height - wm_height) // 2
                    if abs(wm_pos_y - center_y) <= snap_dist:
                        self.watermark_pos.setY(center_y)
            
            # 确保水印完全在图片范围内（避免重复访问属性）
            self.watermark_pos.setX(max(0, min(self.watermark_pos.x(), max_x)))
            self.watermark_pos.setY(max(0, min(self.watermark_pos.y(), max_y)))
            
            logger.debug(f"水印位置已调整: {self.watermark_pos}, 图片尺寸: {img_width}x{img_height}")
            
    def update_position(self, pos: QPoint):
        """更新水印位置"""
        self.watermark_pos = pos
        self.ensure_valid_position()
        self.update()
        self.position_changed.emit(self.watermark_pos)


class PreviewPanel(QWidget):
    """预览面板"""
    
    position_changed = pyqtSignal(QPoint)  # 水印位置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_watermark_position = QPoint(50, 50)  # 当前水印位置
        self.watermark_size = QPoint(100, 50)  # 水印大小
        self.original_pixmap = None
        self.watermarked_pixmap = None
        self.zoom_factor = 1.0  # 缩放系数，默认为100%且固定不变
        self.zoom_levels = [1.0]  # 仅保留100%缩放级别，固定不允许调整
        self._is_dragging = False
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
        # 连接拖拽开始/结束信号用于优化缩放刷新
        self.watermarked_label.drag_started.connect(lambda: setattr(self, '_is_dragging', True))
        self.watermarked_label.drag_finished.connect(self._on_drag_finished)
        
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
    
    def on_watermark_position_changed(self, position: QPoint):
        """水印位置改变处理 - 优化版，减少计算和提升拖拽流畅性"""
        try:
            # 在拖拽过程中减少对图片尺寸的频繁获取
            if hasattr(self, '_cached_image_size'):
                img_width, img_height = self._cached_image_size
            else:
                # 获取实际图片尺寸
                if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
                    img_width = self.watermarked_pixmap.width()
                    img_height = self.watermarked_pixmap.height()
                    # 缓存图片尺寸，减少重复获取
                    self._cached_image_size = (img_width, img_height)
                else:
                    img_width, img_height = 0, 0
                    self._cached_image_size = (img_width, img_height)
                
            # 存储实际位置（考虑缩放因素）
            actual_position = QPoint(int(position.x() / self.zoom_factor), int(position.y() / self.zoom_factor))
            
            # 避免不必要的更新
            if hasattr(self, '_last_pos') and self._last_pos == actual_position:
                return
            
            self.current_watermark_position = actual_position
            
            # 确保水印位置在图片范围内
            if img_width > 0 and img_height > 0:
                # 计算实际图片尺寸下的最大位置
                wm_width, wm_height = int(self.watermark_size.x()), int(self.watermark_size.y())
                max_x = max(0, img_width - wm_width)
                max_y = max(0, img_height - wm_height)
                
                # 限制实际位置在有效范围内 - 使用更简洁的写法
                real_x = actual_position.x()
                real_y = actual_position.y()
                real_x = real_x if real_x > 0 and real_x < max_x else (0 if real_x <= 0 else max_x)
                real_y = real_y if real_y > 0 and real_y < max_y else (0 if real_y <= 0 else max_y)
                
                actual_position.setX(real_x)
                actual_position.setY(real_y)
                
                # 同步更新当前位置
                self.current_watermark_position = actual_position
            
            # 减少日志频率，只在位置变化较大时记录
            if hasattr(self, '_last_logged_pos'):
                last_x, last_y = self._last_logged_pos
                if abs(actual_position.x() - last_x) > 10 or abs(actual_position.y() - last_y) > 10:
                    logger.debug(f"水印位置已改变: {self.current_watermark_position}")
                    self._last_logged_pos = (actual_position.x(), actual_position.y())
            else:
                logger.debug(f"水印位置已改变: {self.current_watermark_position}")
                self._last_logged_pos = (actual_position.x(), actual_position.y())
            
            # 保存上次位置以避免不必要的更新
            self._last_pos = actual_position
            
            # 发送实际位置信号
            self.position_changed.emit(actual_position)
        except Exception as e:
            logger.error(f"处理水印位置变化时出错: {str(e)}")
    
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
        """缩放滑块变化处理 - 现在已禁用缩放功能"""
        pass
        
    def on_zoom_combo_changed(self, index):
        """缩放下拉框变化处理 - 现在已禁用缩放功能"""
        pass
            
    def update_zoom_display(self):
        """更新缩放显示 - 优化版，减少计算和提升性能"""
        try:
            # 避免在拖拽过程中频繁调用此方法
            if hasattr(self, '_is_dragging') and self._is_dragging:
                # 只在拖拽结束后才完全更新
                return
                
            # 获取图片尺寸（优先使用缓存）
            if hasattr(self, '_cached_image_size'):
                img_width, img_height = self._cached_image_size
            else:
                if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
                    img_width = self.watermarked_pixmap.width()
                    img_height = self.watermarked_pixmap.height()
                    self._cached_image_size = (img_width, img_height)
                else:
                    img_width, img_height = 0, 0
                    self._cached_image_size = (img_width, img_height)
                
            if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
                # 获取预览区域的实际可用尺寸
                scroll_area_size = self.watermarked_scroll.viewport().size()
                
                    # 固定使用100%缩放（但保持自动适应窗口大小的功能）
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
                    
                    # 拖拽时使用更快的变换模式
                    transform_mode = Qt.TransformationMode.FastTransformation if hasattr(self, '_is_dragging') and self._is_dragging else Qt.TransformationMode.SmoothTransformation
                    scaled_pixmap = self.watermarked_pixmap.scaled(
                        scaled_width, scaled_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        transform_mode
                    )
                    self.watermarked_label.setPixmap(scaled_pixmap)
                else:
                    # 图片尺寸合适，直接显示原始图片
                    self.watermarked_label.setPixmap(self.watermarked_pixmap)
                
                self.watermarked_label.setText("")
                
                # 高效更新水印大小和位置以适应缩放
                # 只在必要时才更新水印大小
                if not hasattr(self, '_last_watermark_size') or self._last_watermark_size != self.watermark_size:
                    scaled_watermark_width = int(self.watermark_size.x() * self.zoom_factor)
                    scaled_watermark_height = int(self.watermark_size.y() * self.zoom_factor)
                    self.watermarked_label.set_watermark_size(QPoint(scaled_watermark_width, scaled_watermark_height))
                    self._last_watermark_size = self.watermark_size
                
                # 同步水印位置
                if self.current_watermark_position:
                    scaled_pos = QPoint(
                        int(self.current_watermark_position.x() * self.zoom_factor),
                        int(self.current_watermark_position.y() * self.zoom_factor)
                    )
                    # 只在位置变化时才更新
                    if hasattr(self, '_last_watermark_pos') and self._last_watermark_pos == scaled_pos:
                        pass
                    else:
                        self.watermarked_label.set_watermark_position(scaled_pos)
                        self._last_watermark_pos = scaled_pos
                
            # 减少日志频率
            if img_width > 0 and img_height > 0:
                if hasattr(self, '_last_logged_zoom'):
                    if abs(self.zoom_factor - self._last_logged_zoom) > 0.1:
                        display_width = int(img_width * self.zoom_factor)
                        display_height = int(img_height * self.zoom_factor)
                        logger.debug(f"缩放已更新: {self.zoom_factor}, 显示尺寸: {display_width}x{display_height}")
                        self._last_logged_zoom = self.zoom_factor
                else:
                    display_width = int(img_width * self.zoom_factor)
                    display_height = int(img_height * self.zoom_factor)
                    logger.debug(f"缩放已更新: {self.zoom_factor}, 显示尺寸: {display_width}x{display_height}")
                    self._last_logged_zoom = self.zoom_factor
                    
        except Exception as e:
            logger.error(f"更新缩放显示时出错: {str(e)}")
    
    def _on_drag_finished(self):
        """拖拽结束时刷新缩放显示"""
        self._is_dragging = False
        # 拖拽结束后做一次完整的缩放刷新，确保清晰显示
        self.update_zoom_display()

    def ensure_image_fully_visible(self):
        """确保图片能够完整显示在预览窗口中 - 固定使用100%缩放"""
        if self.watermarked_pixmap and not self.watermarked_pixmap.isNull():
            # 直接调用update_zoom_display来确保图片正确显示（会自动适应窗口大小）
            self.update_zoom_display()