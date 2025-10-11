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
                        "text": "PhotoMark2",
                        "font": "Arial",
                        "size": 200,
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
            print(f"加载默认设置失败: {e}")
            return {}
    
    def save_settings(self, settings, file_path):
        """保存设置到文件"""
        try:
            # 验证settings参数
            if not isinstance(settings, dict):
                print("保存设置失败: 设置数据必须是字典类型")
                return False
            
            # 确保输出目录存在
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
                
            # 确保文件扩展名为.json
            if not file_path.endswith('.json'):
                file_path += '.json'
                
            # 深拷贝settings以避免修改原始数据
            import copy
            settings_copy = copy.deepcopy(settings)
            
            # 确保必要的字段存在并具有合理的默认值
            if 'text_watermark' in settings_copy:
                text_settings = settings_copy['text_watermark']
                # 检查并处理QColor对象
                if 'color' in text_settings:
                    from PyQt6.QtGui import QColor
                    if isinstance(text_settings['color'], QColor):
                        # 将QColor对象转换为十六进制字符串
                        text_settings['color'] = text_settings['color'].name()
                elif 'color' not in text_settings or not text_settings['color']:
                    text_settings['color'] = '#FFFFFF'
                    
            # 处理图片水印路径，转换为相对路径
            if 'image_watermark' in settings_copy and 'watermark_path' in settings_copy['image_watermark']:
                watermark_path = settings_copy['image_watermark']['watermark_path']
                if watermark_path and os.path.isabs(watermark_path):
                    # 获取项目根目录
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    # 转换为相对路径
                    try:
                        relative_path = os.path.relpath(watermark_path, project_root)
                        settings_copy['image_watermark']['watermark_path'] = relative_path
                    except ValueError:
                        # 如果无法转换（例如跨驱动器），保留原始路径
                        pass
                    
            # 尝试JSON序列化以验证数据结构
            try:
                json.dumps(settings_copy)
            except (TypeError, OverflowError) as json_err:
                print(f"保存设置失败: 数据结构无法序列化: {json_err}")
                return False
                
            # 保存设置文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_copy, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def load_settings(self, file_path):
        """从文件加载设置"""
        try:
            # 验证文件路径
            if not os.path.exists(file_path):
                print(f"加载设置失败: 文件不存在: {file_path}")
                return {}
                
            # 验证文件扩展名
            if not file_path.endswith('.json'):
                print(f"加载设置失败: 文件必须是JSON格式: {file_path}")
                return {}
                
            # 读取并解析JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            # 验证settings是字典类型
            if not isinstance(settings, dict):
                print("加载设置失败: 配置数据不是有效的字典格式")
                return {}
                
            # 确保必要的字段存在
            if 'text_watermark' in settings:
                text_settings = settings['text_watermark']
                if 'color' not in text_settings or not text_settings['color']:
                    text_settings['color'] = '#FFFFFF'
                else:
                    # 将颜色字符串转换为QColor对象
                    from PyQt6.QtGui import QColor
                    if isinstance(text_settings['color'], str):
                        try:
                            text_settings['color'] = QColor(text_settings['color'])
                        except Exception as e:
                            print(f"解析颜色值失败: {e}")
                            text_settings['color'] = QColor('#FFFFFF')
                            
            return settings
        except json.JSONDecodeError as json_err:
            print(f"加载设置失败: JSON格式错误: {json_err}")
            return {}
        except Exception as e:
            print(f"加载设置失败: {e}")
            return {}