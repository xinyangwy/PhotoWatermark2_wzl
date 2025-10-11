#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试路径转换功能的脚本
"""

import os
from src.utils.config_manager import ConfigManager


def test_path_conversion():
    """测试相对路径转换功能"""
    print("开始测试路径转换功能...")
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 准备测试数据
    project_root = os.path.dirname(os.path.abspath(__file__))
    test_watermark_path = os.path.join(project_root, 'resources', 'watermarks', '星星.png')
    
    if not os.path.exists(test_watermark_path):
        print(f"警告: 测试水印文件不存在: {test_watermark_path}")
        # 尝试使用其他水印文件
        watermark_dir = os.path.join(project_root, 'resources', 'watermarks')
        if os.path.exists(watermark_dir):
            watermark_files = [f for f in os.listdir(watermark_dir) if f.endswith('.png')]
            if watermark_files:
                test_watermark_path = os.path.join(watermark_dir, watermark_files[0])
                print(f"使用替代水印文件: {test_watermark_path}")
    
    # 测试1: 保存设置，检查是否转换为相对路径
    test_settings = {
        'image_watermark': {
            'watermark_path': test_watermark_path,
            'scale': 50,
            'opacity': 80
        },
        'watermark_type': 'image'
    }
    
    test_config_file = os.path.join(project_root, 'config', 'test_path.json')
    
    # 保存设置
    save_result = config_manager.save_settings(test_settings, test_config_file)
    print(f"保存设置结果: {save_result}")
    
    # 加载保存的设置，检查路径
    if save_result:
        loaded_settings = config_manager.load_settings(test_config_file)
        if 'image_watermark' in loaded_settings and 'watermark_path' in loaded_settings['image_watermark']:
            saved_path = loaded_settings['image_watermark']['watermark_path']
            print(f"保存的水印路径: {saved_path}")
            print(f"是否为相对路径: {not os.path.isabs(saved_path)}")
            
            # 验证相对路径是否正确
            if not os.path.isabs(saved_path):
                # 构建绝对路径进行验证
                abs_path_from_relative = os.path.join(project_root, saved_path)
                print(f"从相对路径构建的绝对路径: {abs_path_from_relative}")
                print(f"路径是否存在: {os.path.exists(abs_path_from_relative)}")
            
            # 清理测试文件
            if os.path.exists(test_config_file):
                os.remove(test_config_file)
                print(f"已清理测试文件: {test_config_file}")
    
    # 测试2: 检查文本水印默认字号是否为200
    default_settings = config_manager.load_default_settings()
    if 'text_watermark' in default_settings and 'size' in default_settings['text_watermark']:
        default_font_size = default_settings['text_watermark']['size']
        print(f"\n文本水印默认字号: {default_font_size}")
        print(f"默认字号是否为200: {default_font_size == 200}")

    print("\n测试完成!")


if __name__ == '__main__':
    test_path_conversion()