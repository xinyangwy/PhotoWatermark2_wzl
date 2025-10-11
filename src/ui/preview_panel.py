#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
预览面板组件
支持原图和带水印图片的显示
"""

import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap

# 配置日志
logger = logging.getLogger(__name__)


class PreviewPanel(QWidget):
    """预览面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_watermark_position = QPoint(50, 50)  # 当前水印位置
        self.watermark_size = QPoint(100, 50)  # 水印大小
        self.original_pixmap = None
        self.watermarked_pixmap = None
        self.zoom_factor = 1.0  # 缩放系数，默认为100%且固定不变
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 水印预览区域（使用普通标签）
        self.watermarked_scroll = QScrollArea()
        self.watermarked_label = QLabel()
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
        self.current_watermark_position = position
    
    def set_watermark_size(self, size: QPoint):
        """设置水印大小"""
        self.watermark_size = size
    
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