# PhotoWatermark2

A powerful and user-friendly image watermark tool built with Python and PyQt6.

## Features

- **Text Watermark**: Add customizable text watermarks with options for font, size, color, transparency, rotation, and position
- **Image Watermark**: Add image-based watermarks from predefined options or custom images
- **Batch Processing**: Apply watermarks to multiple images simultaneously
- **Visual Preview**: See real-time previews of watermarks before applying
- **Tiling Mode**: Create watermark patterns that tile across the entire image
- **User-Friendly Interface**: Intuitive GUI with drag-and-drop support

## System Requirements

- Python 3.8 or higher
- PyQt6
- Pillow
- NumPy

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/xinyangwy/PhotoWatermark2_wzl.git
cd PhotoWatermark2_wzl
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

Run the application using Python:

```bash
python main.py
```

### Adding Text Watermarks
1. Select image(s) by clicking the "Add Image" button or dragging and dropping
2. Switch to the "Text Watermark" tab
3. Enter your watermark text
4. Customize font, size, color, transparency, rotation, and position
5. Preview the watermark in the preview panel
6. Click "Apply Watermark" to process the image(s)

### Adding Image Watermarks
1. Select image(s) by clicking the "Add Image" button or dragging and dropping
2. Switch to the "Image Watermark" tab
3. Choose a predefined watermark or upload your own
4. Adjust size, transparency, rotation, and position
5. Preview the watermark in the preview panel
6. Click "Apply Watermark" to process the image(s)

## Project Structure

```
PhotoWatermark2_wzl/
├── main.py               # Application entry point
├── PhotoMark_PRD.md      # Product Requirements Document
├── requirements.txt      # Project dependencies
├── resources/            # Resource files
│   ├── icon.ico          # Application icon
│   └── watermarks/       # Predefined watermark images
└── src/                  # Source code
    ├── app.py            # Main application logic
    ├── core/             # Core functionality
    │   └── watermark_processor.py  # Watermark processing logic
    ├── ui/               # User interface components
    │   ├── image_list_panel.py     # Image list panel
    │   ├── preview_panel.py        # Preview panel
    │   └── watermark_panel.py      # Watermark settings panel
    └── utils/            # Utility functions
        ├── config_manager.py       # Configuration management
        └── resource_manager.py     # Resource management
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to improve the project.

## Acknowledgements

- PyQt6 for the graphical user interface
- Pillow for image processing capabilities