# PhotoWatermark2

一个功能强大且用户友好的图片水印工具，使用Python和PyQt6构建。

## 功能特点

- **文本水印**：添加可自定义的文本水印，支持字体、大小、颜色、透明度、旋转和位置调整
- **图片水印**：添加基于图片的水印，支持预定义选项或自定义图片
- **批量处理**：同时为多张图片添加水印
- **视觉预览**：应用前查看水印的实时预览效果
- **平铺模式**：创建在整个图片上平铺的水印图案
- **友好的用户界面**：直观的GUI界面，支持拖放操作

## 系统要求

- Python 3.8 或更高版本
- PyQt6
- Pillow
- NumPy

## 安装方法

### 1. 克隆仓库

```bash
git clone https://github.com/xinyangwy/PhotoWatermark2_wzl.git
cd PhotoWatermark2_wzl
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

使用Python运行应用程序：

```bash
python main.py
```

### 添加文本水印
1. 通过点击"添加图片"按钮或拖放方式选择图片
2. 切换到"文本水印"选项卡
3. 输入您的水印文本
4. 自定义字体、大小、颜色、透明度、旋转角度和位置
5. 在预览面板中查看水印效果
6. 点击"应用水印"处理图片

### 添加图片水印
1. 通过点击"添加图片"按钮或拖放方式选择图片
2. 切换到"图片水印"选项卡
3. 选择预定义水印或上传您自己的水印图片
4. 调整大小、透明度、旋转角度和位置
5. 在预览面板中查看水印效果
6. 点击"应用水印"处理图片

## 项目结构

```
PhotoWatermark2_wzl/
├── main.py               # 应用程序入口
├── PhotoMark_PRD.md      # 产品需求文档
├── requirements.txt      # 项目依赖
├── resources/            # 资源文件
│   ├── icon.ico          # 应用程序图标
│   └── watermarks/       # 预定义水印图片
└── src/                  # 源代码
    ├── app.py            # 主应用程序逻辑
    ├── core/             # 核心功能
    │   └── watermark_processor.py  # 水印处理逻辑
    ├── ui/               # 用户界面组件
    │   ├── image_list_panel.py     # 图片列表面板
    │   ├── preview_panel.py        # 预览面板
    │   └── watermark_panel.py      # 水印设置面板
    └── utils/            # 实用函数
        ├── config_manager.py       # 配置管理
        └── resource_manager.py     # 资源管理
```

## 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 贡献指南

欢迎贡献！请随时提交pull request或提出issue来改进项目。

## 致谢

- PyQt6 提供图形用户界面
- Pillow 提供图像处理功能