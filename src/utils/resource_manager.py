#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源文件管理模块
"""

import os
import sys
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QDir


class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        # 获取资源目录路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件
            self.resource_dir = os.path.join(os.path.dirname(sys.executable), 'resources')
        else:
            # 如果是源码运行
            self.resource_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'resources')
            
        # 确保资源目录路径存在
        self.resource_dir = os.path.abspath(self.resource_dir)
        
    def get_resource_path(self, relative_path):
        """
        获取资源文件的绝对路径
        
        Args:
            relative_path: 相对于资源目录的路径
            
        Returns:
            str: 资源文件的绝对路径
        """
        return os.path.join(self.resource_dir, relative_path)
        
    def get_icon(self, icon_name):
        """
        获取图标
        
        Args:
            icon_name: 图标文件名
            
        Returns:
            QIcon: 图标对象
        """
        icon_path = self.get_resource_path(f'icons/{icon_name}')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()  # 返回空图标
        
    def get_watermark(self, watermark_name):
        """
        获取水印图片
        
        Args:
            watermark_name: 水印文件名
            
        Returns:
            QPixmap: 水印图片对象
        """
        watermark_path = self.get_resource_path(f'watermarks/{watermark_name}')
        if os.path.exists(watermark_path):
            return QPixmap(watermark_path)
        return QPixmap()  # 返回空图片
        
    def list_watermarks(self):
        """
        列出所有可用的水印文件
        
        Returns:
            list: 水印文件名列表
        """
        watermarks_dir = self.get_resource_path('watermarks')
        if not os.path.exists(watermarks_dir):
            return []
            
        watermarks = []
        for file_name in os.listdir(watermarks_dir):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                watermarks.append(file_name)
                
        return watermarks
        
    def get_app_icon(self):
        """
        获取应用程序图标
        
        Returns:
            QIcon: 应用程序图标
        """
        icon_path = self.get_resource_path('icon.ico')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()  # 返回空图标