if image_path in self.image_paths:
    self.image_paths.remove(image_path)
else:
    logger.warning(f"尝试移除不存在的图片路径: {image_path}")