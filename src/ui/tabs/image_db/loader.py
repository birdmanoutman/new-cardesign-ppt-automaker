from PyQt6.QtCore import QThread, pyqtSignal
import os

class ImageLoader(QThread):
    """图片加载线程"""
    image_loaded = pyqtSignal(dict, str)  # 发送图片信息和缩略图路径
    batch_finished = pyqtSignal()
    progress_updated = pyqtSignal(int, int)  # 当前进度, 总数

    def __init__(self, image_processor, images, batch_size=50):
        super().__init__()
        self.image_processor = image_processor
        self.images = images
        self.batch_size = batch_size
        self.is_running = True

    def stop(self):
        """停止线程"""
        self.is_running = False
        if self.isRunning():
            self.quit()
            if not self.wait(1000):  # 等待1秒
                print("线程未能正常停止，强制终止")
                self.terminate()
                self.wait()

    def run(self):
        try:
            total = len(self.images)
            for i in range(0, total, self.batch_size):
                if not self.is_running:
                    return
                    
                batch = self.images[i:i + self.batch_size]
                for img_info in batch:
                    if not self.is_running:
                        return
                        
                    try:
                        if not os.path.exists(img_info['path']):
                            continue
                        
                        # 获取或创建缩略图
                        thumb_path = self.image_processor._create_thumbnail_with_badge(
                            img_info['path'], 
                            img_info.get('ref_count', 0)
                        )
                        
                        if self.is_running:  # 再次检查，确保线程仍在运行
                            self.image_loaded.emit(img_info, thumb_path)
                            self.progress_updated.emit(i + 1, total)
                        
                    except Exception as e:
                        print(f"加载图片失败: {str(e)}")
                        continue
                
                # 每批次完成后发送信号
                if self.is_running:
                    self.batch_finished.emit()
            
            if self.is_running:
                self.batch_finished.emit()
        except Exception as e:
            print(f"图片加载线程出错: {str(e)}")
        finally:
            self.is_running = False
