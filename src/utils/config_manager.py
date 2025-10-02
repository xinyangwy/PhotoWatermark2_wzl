#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块
"""

import json
import os
from PyQt6.QtCore import QStandardPaths, QDir


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file=None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if config_file is None:
            # 获取应用程序数据目录
            data_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation)
            # 确保目录存在
            QDir().mkpath(data_dir)
            self.config_file = os.path.join(data_dir, 'config.json')
        else:
            self.config_file = config_file
            
        self.config = {}
        self.load_config()
        
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.config = {}
        else:
            # 默认配置
            self.config = {
                "recent_files": [],
                "output_directory": "./output",
                "default_settings": {
                    "text_watermark": {
                        "text": "水印文字",
                        "font": "Arial",
                        "size": 24,
                        "bold": False,
                        "italic": False,
                        "color": "#FFFFFF",
                        "opacity": 100
                    },
                    "image_watermark": {
                        "scale": 100,
                        "opacity": 100
                    },
                    "position": "right_bottom",
                    "export": {
                        "format": "JPEG",
                        "quality": 90,
                        "prefix": "",
                        "suffix": "_watermark"
                    }
                }
            }
            
    def save_config(self):
        """保存配置"""
        try:
            # 确保配置文件目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
            
    def get(self, key, default=None):
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key, value):
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 遍历到倒数第二个键，创建必要的嵌套字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # 设置最终的键值
        config[keys[-1]] = value
        
    def add_recent_file(self, file_path):
        """
        添加最近打开的文件
        
        Args:
            file_path: 文件路径
        """
        recent_files = self.config.get('recent_files', [])
        
        # 如果文件已存在，移到列表开头
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        
        # 限制最近文件数量为10个
        recent_files = recent_files[:10]
        
        self.config['recent_files'] = recent_files
        
    def get_recent_files(self):
        """
        获取最近打开的文件列表
        
        Returns:
            list: 文件路径列表
        """
        return self.config.get('recent_files', [])
        
    def clear_recent_files(self):
        """清空最近打开的文件列表"""
        self.config['recent_files'] = []
    
    def load_default_settings(self):
        """加载默认设置"""
        try:
            return self.config.get('default_settings', {})
        except Exception as e:
            logger.error(f"加载默认设置失败: {e}")
            return {}
    
    def save_settings(self, settings, file_path):
        """保存设置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def load_settings(self, file_path):
        """从文件加载设置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载设置失败: {e}")
            return {}