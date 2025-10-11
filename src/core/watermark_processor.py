#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
水印处理核心模块
支持文本水印和图片水印，提供多种布局和效果选项
"""

import os
import logging
import warnings
from typing import Optional, Tuple, Dict, Any
from PyQt6.QtGui import QImage, QPixmap, QPainter, QFont, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# 忽略libpng警告
warnings.filterwarnings("ignore", category=UserWarning, message="iCCP: known incorrect sRGB profile")

logger = logging.getLogger(__name__)


class WatermarkProcessor:
    """水印处理器 - 支持文本和图片水印"""
    
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        
    def add_text_watermark(self, image_path: str, watermark_text: str, 
                          settings: Dict[str, Any]) -> Optional[QPixmap]:
        """
        添加文本水印
        
        Args:
            image_path: 原图片路径
            watermark_text: 水印文本
            settings: 水印设置字典
                - font_family/font: 字体名称 (默认: Arial)
                - font_size/size: 字体大小 (默认: 24)
                - bold: 是否粗体 (默认: False)
                - italic: 是否斜体 (默认: False)
                - color: 文本颜色 (默认: 白色)
                - opacity: 透明度 0-100 (默认: 80)
                - position: 位置 ('center', 'top-left', 'top-right', 'bottom-left', 'bottom-right')
                - rotation: 旋转角度 -360到360 (默认: 0)
                - background: 背景颜色 (可选)
                - background_opacity: 背景透明度 0-100 (默认: 50)
                - padding/margin: 内边距 (默认: 10)
                - log_level: 日志级别 ('info', 'debug', 'silent')，默认 'info'
                
        Returns:
            QPixmap: 添加水印后的图片，失败返回None
        """
        try:
            # 验证输入
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return None
                
            if not watermark_text.strip():
                logger.warning("水印文本为空")
                return None
                
            # 加载原图
            image = QImage(image_path)
            if image.isNull():
                logger.error(f"无法加载图片: {image_path}")
                return None
                
            # 创建绘图设备
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            # 设置字体 - 兼容新旧参数名
            font_family = settings.get('font_family', settings.get('font', 'Arial'))
            # 如果用户没有指定字体大小，使用图片宽度的八分之一作为默认值
            if 'font_size' not in settings and 'size' not in settings:
                default_font_size = max(20, image.width() // 8)  # 确保至少20号字体
                font_size = default_font_size
            else:
                font_size = settings.get('font_size', settings.get('size', 24))
            bold = settings.get('bold', False)
            italic = settings.get('italic', False)
            
            font = QFont(font_family, font_size)
            font.setBold(bold)
            font.setItalic(italic)
            painter.setFont(font)
            
            # 计算文本尺寸
            font_metrics = painter.fontMetrics()
            text_width = font_metrics.horizontalAdvance(watermark_text)
            text_height = font_metrics.height()
            
            # 设置颜色和透明度
            color = self._parse_color(settings.get('color', '#FFFFFF'))
            opacity = settings.get('opacity', 80) / 100.0
            color.setAlphaF(opacity)
            
            # 处理平铺模式 - 兼容新旧参数名
            tiling = settings.get('tiling', settings.get('tile_mode', False))
            if tiling:
                # 创建虚拟水印图片
                watermark_image = QImage(text_width, text_height, QImage.Format.Format_ARGB32)
                watermark_image.fill(Qt.GlobalColor.transparent)
                temp_painter = QPainter(watermark_image)
                temp_painter.setFont(font)
                temp_painter.setPen(QPen(color))
                temp_painter.drawText(0, text_height - font_metrics.descent(), watermark_text)
                temp_painter.end()
                
                # 应用平铺水印
                self._apply_tiling_watermark(painter, image, watermark_image, settings)
            else:
                # 单张水印模式
                position = settings.get('position', 'center')
                padding = settings.get('padding', settings.get('margin', 10))
                x, y = self._calculate_position(image.width(), image.height(), 
                                              text_width, text_height, position, padding, settings)
                
                # 绘制背景（如果设置）
                # 兼容新旧参数名：bg_color/bg_opacity 或 background/background_opacity
                if settings.get('background') or settings.get('bg_color'):
                    # 优先使用bg_color
                    bg_color_value = settings.get('bg_color', settings.get('background', '#000000'))
                    bg_color = self._parse_color(bg_color_value)
                    
                    # 优先使用bg_opacity
                    bg_opacity_value = settings.get('bg_opacity', settings.get('background_opacity', 50))
                    bg_opacity = bg_opacity_value / 100.0
                    bg_color.setAlphaF(bg_opacity)
                    
                    bg_rect = QRect(x - padding, y - padding, 
                                  text_width + 2*padding, text_height + 2*padding)
                    painter.fillRect(bg_rect, QBrush(bg_color))
                
                # 应用旋转
                rotation = settings.get('rotation', 0)
                if rotation != 0:
                    painter.save()
                    painter.translate(x + text_width/2, y + text_height/2)
                    painter.rotate(rotation)
                    painter.translate(-(x + text_width/2), -(y + text_height/2))
                
                # 设置画笔和绘制文本
                painter.setPen(QPen(color))
                painter.drawText(x, y + text_height - font_metrics.descent(), watermark_text)
                
                # 恢复旋转状态
                if rotation != 0:
                    painter.restore()
            
            painter.end()
            
            # 根据设置控制日志输出
            log_level = settings.get('log_level', 'info')
            if log_level == 'info':
                logger.info(f"成功添加文本水印到: {image_path}")
            elif log_level == 'debug':
                logger.debug(f"成功添加文本水印到: {image_path}")
            # 'silent' 模式不记录日志
            
            return QPixmap.fromImage(image)
            
        except Exception as e:
            logger.error(f"添加文本水印失败: {str(e)}")
            return None
    
    def add_image_watermark(self, image_path: str, watermark_path: str, 
                           settings: Dict[str, Any]) -> Optional[QPixmap]:
        """
        添加图片水印
        
        Args:
            image_path: 原图片路径
            watermark_path: 水印图片路径
            settings: 水印设置字典
                - scale: 缩放比例 1-100 (默认: 20)
                - opacity: 透明度 0-100 (默认: 80)
                - position: 位置 ('center', 'top-left', 'top-right', 'bottom-left', 'bottom-right')
                - rotation: 旋转角度 -360到360 (默认: 0)
                - tiling/tile_mode: 是否平铺 (默认: False)
                - tiling_spacing/tile_spacing: 平铺间距 (默认: 50)
                - log_level: 日志级别 ('info', 'debug', 'silent')，默认 'info'
                
        Returns:
            QPixmap: 添加水印后的图片，失败返回None
        """
        try:
            # 验证输入
            if not os.path.exists(image_path):
                logger.error(f"原图片文件不存在: {image_path}")
                return None
                
            if not watermark_path:
                logger.error("水印图片文件不存在: 未指定水印图片路径")
                return None
            
            # 处理相对路径
            if not os.path.isabs(watermark_path):
                # 获取项目根目录
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                # 构建绝对路径
                watermark_path = os.path.join(project_root, watermark_path)
                
            if not os.path.exists(watermark_path):
                logger.error(f"水印图片文件不存在: {watermark_path}")
                return None
                
            # 加载原图
            image = QImage(image_path)
            if image.isNull():
                logger.error(f"无法加载原图片: {image_path}")
                return None
                
            # 加载水印图片
            watermark = QImage(watermark_path)
            if watermark.isNull():
                logger.error(f"无法加载水印图片: {watermark_path}")
                return None
                
            # 应用缩放
            scale = settings.get('scale', 20) / 100.0
            if scale != 1.0:
                new_width = int(watermark.width() * scale)
                new_height = int(watermark.height() * scale)
                watermark = watermark.scaled(new_width, new_height, 
                                           Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
            
            # 创建绘图设备
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            # 应用透明度
            opacity = settings.get('opacity', 80) / 100.0
            painter.setOpacity(opacity)
            
            # 处理平铺模式 - 兼容新旧参数名
            tiling = settings.get('tiling', settings.get('tile_mode', False))
            if tiling:
                self._apply_tiling_watermark(painter, image, watermark, settings)
            else:
                # 单张水印模式
                position = settings.get('position', 'center')
                padding = settings.get('padding', settings.get('margin', 20))
                x, y = self._calculate_position(image.width(), image.height(), 
                                              watermark.width(), watermark.height(), 
                                              position, padding, settings)
                
                # 应用旋转
                rotation = settings.get('rotation', 0)
                if rotation != 0:
                    painter.save()
                    painter.translate(x + watermark.width()/2, y + watermark.height()/2)
                    painter.rotate(rotation)
                    painter.translate(-(x + watermark.width()/2), -(y + watermark.height()/2))
                
                # 绘制水印
                painter.drawImage(x, y, watermark)
                
                if rotation != 0:
                    painter.restore()
            
            painter.end()
            
            # 根据设置控制日志输出
            log_level = settings.get('log_level', 'info')
            if log_level == 'info':
                logger.info(f"成功添加图片水印到: {image_path}")
            elif log_level == 'debug':
                logger.debug(f'当前应用范围设置: apply_to_all={settings.get("apply_to_all")}')
            # 'silent' 模式不记录日志
            
            return QPixmap.fromImage(image)
            
        except Exception as e:
            logger.error(f"添加图片水印失败: {str(e)}")
            return None
    
    def _apply_tiling_watermark(self, painter: QPainter, image: QImage, 
                               watermark: QImage, settings: Dict[str, Any]):
        """应用平铺水印效果"""
        spacing = settings.get('tiling_spacing', settings.get('tile_spacing', 50))
        
        watermark_width = watermark.width()
        watermark_height = watermark.height()
        
        # 计算平铺的行列数
        cols = (image.width() + spacing) // (watermark_width + spacing)
        rows = (image.height() + spacing) // (watermark_height + spacing)
        
        for row in range(rows + 1):
            for col in range(cols + 1):
                x = col * (watermark_width + spacing)
                y = row * (watermark_height + spacing)
                
                # 交错排列
                if row % 2 == 1:
                    x += watermark_width // 2
                
                painter.drawImage(x, y, watermark)
    
    def _calculate_position(self, image_width: int, image_height: int, 
                           watermark_width: int, watermark_height: int, 
                           position: str, padding: int, settings: Dict[str, Any] = None) -> Tuple[int, int]:
        """计算水印位置"""
        
        # 处理自定义位置
        if position == 'custom' and settings:
            # 优先使用x, y (从拖拽更新)
            if 'x' in settings and 'y' in settings and settings['x'] is not None and settings['y'] is not None:
                x = int(settings['x'])
                y = int(settings['y'])
            else:
                # 兼容旧代码，使用custom_x, custom_y
                custom_x = settings.get('custom_x', 0)
                custom_y = settings.get('custom_y', 0)
                x = int(custom_x)
                y = int(custom_y)
            
            # 确保在图片范围内
            x = max(0, min(x, image_width - watermark_width))
            y = max(0, min(y, image_height - watermark_height))
            return (x, y)
        
        # 预设位置（兼容下划线和连字符格式）
        position_mapping = {
            'top_left': 'top-left',
            'top_center': 'top-center', 
            'top_right': 'top-right',
            'center_left': 'center-left',
            'center': 'center',
            'center_right': 'center-right',
            'bottom_left': 'bottom-left',
            'bottom_center': 'bottom-center',
            'bottom_right': 'bottom-right'
        }
        
        # 标准化位置格式
        normalized_position = position_mapping.get(position, position)
        
        positions = {
            'top-left': (padding, padding),
            'top-center': ((image_width - watermark_width) // 2, padding),
            'top-right': (image_width - watermark_width - padding, padding),
            'center-left': (padding, (image_height - watermark_height) // 2),
            'center': ((image_width - watermark_width) // 2, 
                      (image_height - watermark_height) // 2),
            'center-right': (image_width - watermark_width - padding, 
                           (image_height - watermark_height) // 2),
            'bottom-left': (padding, image_height - watermark_height - padding),
            'bottom-center': ((image_width - watermark_width) // 2, 
                            image_height - watermark_height - padding),
            'bottom-right': (image_width - watermark_width - padding, 
                           image_height - watermark_height - padding)
        }
        
        return positions.get(normalized_position, positions['center'])
    
    def _parse_color(self, color_input) -> QColor:
        """解析颜色输入"""
        if isinstance(color_input, QColor):
            return color_input
        elif isinstance(color_input, str):
            if color_input.startswith('#'):
                return QColor(color_input)
            else:
                # 尝试颜色名称
                return QColor(color_input)
        elif isinstance(color_input, (list, tuple)):
            if len(color_input) >= 3:
                return QColor(color_input[0], color_input[1], color_input[2])
        
        return QColor(255, 255, 255)  # 默认白色
    
    def batch_process(self, image_paths: list, watermark_settings: Dict[str, Any], 
                     output_dir: str, watermark_type: str = 'text') -> Dict[str, str]:
        """
        批量处理图片
        
        Args:
            image_paths: 图片路径列表
            watermark_settings: 水印设置
            output_dir: 输出目录
            watermark_type: 水印类型 ('text' 或 'image')
            
        Returns:
            Dict: 处理结果 {原文件路径: 输出文件路径}
        """
        results = {}
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        for i, image_path in enumerate(image_paths):
            try:
                if not os.path.exists(image_path):
                    logger.warning(f"跳过不存在的文件: {image_path}")
                    continue
                
                # 生成输出文件名
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, f"{name}_watermarked{ext}")
                
                # 添加水印
                if watermark_type == 'text':
                    result_pixmap = self.add_text_watermark(image_path, 
                                                           watermark_settings.get('text', ''), 
                                                           watermark_settings)
                else:
                    result_pixmap = self.add_image_watermark(image_path, 
                                                          watermark_settings.get('watermark_path', ''), 
                                                          watermark_settings)
                
                if result_pixmap and not result_pixmap.isNull():
                    # 保存结果
                    result_pixmap.save(output_path)
                    results[image_path] = output_path
                    logger.info(f"处理成功 ({i+1}/{len(image_paths)}): {filename}")
                else:
                    logger.error(f"处理失败: {filename}")
                    
            except Exception as e:
                logger.error(f"处理图片失败 {image_path}: {str(e)}")
        
        return results
    
    def validate_image(self, image_path: str) -> bool:
        """验证图片文件是否有效"""
        try:
            if not os.path.exists(image_path):
                return False
            
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in self.supported_formats:
                return False
            
            # 尝试加载图片
            image = QImage(image_path)
            return not image.isNull()
            
        except Exception:
            return False
    
    def get_image_info(self, image_path: str) -> Optional[Dict[str, Any]]:
        """获取图片信息"""
        try:
            if not self.validate_image(image_path):
                return None
            
            image = QImage(image_path)
            return {
                'width': image.width(),
                'height': image.height(),
                'format': image.format(),
                'size_bytes': os.path.getsize(image_path),
                'file_path': image_path
            }
        except Exception as e:
            logger.error(f"获取图片信息失败: {str(e)}")
            return None