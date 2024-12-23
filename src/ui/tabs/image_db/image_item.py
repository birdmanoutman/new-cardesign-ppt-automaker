from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QIcon
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
from typing import Dict, Optional

class ImageItem:
    """图片项管理类"""
    
    @staticmethod
    def create_item(img_info: dict, thumb_path: str, image_processor) -> Optional[QListWidgetItem]:
        """创建图片项"""
        try:
            if not img_info or not isinstance(img_info, dict):
                print(f"无效的图片信息: {img_info}")
                return None
            
            if not thumb_path:
                print(f"无效的缩略图路径: {thumb_path}")
                return None
            
            # 处理特殊格式
            if thumb_path.lower().endswith(('.wmf', '.emf')):
                # 使用默认图标
                default_icon = str(Path(image_processor.__file__).parent / 'assets' / 'metafile_icon.png')
                if Path(default_icon).exists():
                    pixmap = QPixmap(default_icon)
                else:
                    # 创建简单的占位图标
                    pixmap = QPixmap(200, 200)
                    pixmap.fill(QColor(200, 200, 200))
                    painter = QPainter(pixmap)
                    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "WMF/EMF\nFile")
                    painter.end()
            else:
                # 创建透明背景的图标
                if thumb_path.lower().endswith('.png'):
                    # 使用QImage直接加载PNG
                    qimage = QImage(thumb_path)
                    if qimage.format() != QImage.Format.Format_ARGB32:
                        qimage = qimage.convertToFormat(QImage.Format.Format_ARGB32)
                    pixmap = QPixmap.fromImage(qimage)
                else:
                    pixmap = QPixmap(thumb_path)
                
                if pixmap.isNull():
                    # 如果加载失败，使用错误占位图
                    error_icon = str(Path(image_processor.__file__).parent / 'assets' / 'error_icon.png')
                    if Path(error_icon).exists():
                        pixmap = QPixmap(error_icon)
                    else:
                        # 创建简单的错误图标
                        pixmap = QPixmap(200, 200)
                        pixmap.fill(QColor(255, 200, 200))
                        painter = QPainter(pixmap)
                        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Error\nLoading")
                        painter.end()
                else:
                    # 创建透明背景
                    transparent_pixmap = QPixmap(pixmap.size())
                    transparent_pixmap.fill(Qt.GlobalColor.transparent)
                    
                    # 在透明背景上绘制棋盘格图案
                    painter = QPainter(transparent_pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    
                    # 绘制棋盘格背景
                    cell_size = 8
                    for x in range(0, transparent_pixmap.width(), cell_size):
                        for y in range(0, transparent_pixmap.height(), cell_size):
                            if (x // cell_size + y // cell_size) % 2 == 0:
                                painter.fillRect(x, y, cell_size, cell_size, QColor(235, 235, 235))
                            else:
                                painter.fillRect(x, y, cell_size, cell_size, QColor(255, 255, 255))
                    
                    # 使用CompositionMode_SourceOver确保透明度正确
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                    painter.drawPixmap(0, 0, pixmap)
                    painter.end()
                    
                    # 更新pixmap为带背景的版本
                    pixmap = transparent_pixmap
            
            # 创建列表项
            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            item.setSizeHint(QSize(220, 240))
            
            # 获取图片的标签
            tags = image_processor.tag_manager.get_image_tags(img_info['hash'])
            
            # 构建显示文本
            display_text = [img_info['name']]
            if img_info.get('ref_count', 0) > 1:
                display_text.append(f"[在 {img_info['ref_count']} 个PPT中使用]")
            
            # 添加标签信息
            if tags:
                tag_text = "标签: " + ", ".join(
                    f"{tag['name']}({tag['confidence']:.2f})" 
                    for tag in sorted(tags, key=lambda x: x['confidence'], reverse=True)
                )
                display_text.append(tag_text)
            
            item.setText("\n".join(display_text))
            
            # 设置工具提示
            tooltip = [
                f"文件名: {img_info['name']}",
                f"格式: {img_info.get('format', '未知')}",
                f"尺寸: {img_info.get('width', '?')}x{img_info.get('height', '?')}"
            ]
            
            # 处理文件大小
            file_size = img_info.get('file_size')
            if file_size is not None:
                size_kb = file_size / 1024
                tooltip.append(f"大小: {size_kb:.1f}KB")
            else:
                tooltip.append("大小: 未知")
            
            tooltip.extend([
                f"使用于 {img_info.get('ref_count', 0)} 个PPT中",
                f"提取时间: {img_info.get('extract_date', '未知')}"
            ])
            
            if tags:
                tooltip.append("\n标签:")
                for tag in sorted(tags, key=lambda x: x['confidence'], reverse=True):
                    tooltip.append(
                        f"- {tag['name']} ({tag['confidence']:.2f})"
                        f" [{tag.get('category_name', '未分类')}]"
                    )
            
            item.setToolTip("\n".join(tooltip))
            
            # 保存原始数据
            item.setData(Qt.ItemDataRole.UserRole, img_info)
            
            return item
            
        except Exception as e:
            print(f"创建图片项时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None