#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片水印工具 (PhotoMark)
一款简单易用的本地图片水印处理工具
"""

import sys
import os
import traceback
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox

# 解决Windows控制台中文显示问题
if sys.platform.startswith('win'):
    try:
        # 检查sys.stdout是否存在
        if sys.stdout is not None:
            try:
                # 设置标准输出编码为UTF-8
                sys.stdout.reconfigure(encoding='utf-8')
            except AttributeError:
                # Python 3.6及以下版本兼容性处理
                if hasattr(sys.stdout, 'buffer'):
                    import io
                    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('photomark.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 将src目录添加到Python路径中
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def excepthook(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # 记录异常信息
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"未捕获的异常:\n{error_msg}")
    
    # 显示错误对话框
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(
                None, 
                "应用程序错误", 
                f"程序发生意外错误:\n\n{exc_type.__name__}: {exc_value}\n\n"
                f"详细信息已记录到日志文件。\n"
                f"请重启应用程序。"
            )
    except Exception:
        pass

def main():
    # 设置全局异常处理
    sys.excepthook = excepthook
    
    try:
        from src.app import PhotoMarkApp
        
        app = QApplication(sys.argv)
        app.setApplicationName("PhotoMark")
        app.setApplicationVersion("1.0.0")
        
        # 创建主窗口
        window = PhotoMarkApp()
        window.show()
        
        logger.info("应用程序启动成功")
        
        # 运行应用程序
        return_code = app.exec()
        logger.info("应用程序正常退出")
        return return_code
        
    except Exception as e:
        logger.critical(f"应用程序启动失败: {str(e)}")
        QMessageBox.critical(
            None,
            "启动错误",
            f"应用程序启动失败:\n{str(e)}\n\n请检查日志文件获取详细信息。"
        )
        return 1

if __name__ == '__main__':
    sys.exit(main())