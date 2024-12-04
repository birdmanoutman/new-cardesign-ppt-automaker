from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QGridLayout,
    QSplitter, QListWidget, QListWidgetItem, QWidget, QMenu, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QCheckBox, QDialog, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QPoint, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QImage, QPainter, QColor, QFont, QPen
from PyQt6.QtWidgets import QApplication
import os
from pathlib import Path
from .base_tab import BaseTab
from PIL import Image
import win32clipboard
import win32con
import io
import warnings

# 导入标签管理对话框
from ..dialogs.tag_manager_dialog import TagManagerDialog

warnings.filterwarnings("ignore", category=UserWarning, module="PIL.PngImagePlugin")

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

class ImageDBTab(BaseTab):
    def __init__(self, ppt_processor, parent=None):
        self.ppt_processor = ppt_processor
        super().__init__(parent)
        
        # 初始化完成后直接加载数据
        QTimer.singleShot(100, self._load_database_state)
        
        self.image_loader = None
        self.loaded_images = set()
        
        # 添加分页相关属性
        self.current_page = 0
        self.page_size = 50
        self.is_loading = False
        self.has_more = True
        self.current_filters = None
        
        # 添加快捷键支持
        self.image_grid.keyPressEvent = self._handle_key_press
        
        # 添加线程清理
        self.destroyed.connect(self._cleanup)

    def _cleanup_loader(self):
        """清理加载线程"""
        if self.image_loader:
            self.image_loader.stop()
            self.image_loader.deleteLater()
            self.image_loader = None

    def _cleanup(self):
        """清理资源"""
        try:
            self._cleanup_loader()
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        self._cleanup()
        super().closeEvent(event)

    def _load_database_state(self):
        """加载数据库状态"""
        try:
            image_processor = self.ppt_processor.get_image_processor()
            
            # 加载已有的PPT源文件夹
            for source_path in image_processor.get_ppt_sources():
                if os.path.exists(source_path):
                    row = self.source_table.rowCount()
                    self.source_table.insertRow(row)
                    self.source_table.setItem(row, 0, QTableWidgetItem(source_path))
                    self.source_table.setItem(row, 1, QTableWidgetItem("已添加"))
            
            # 加载图片库路径
            lib_path = image_processor.get_setting('image_lib_path')
            if lib_path:
                self.image_lib_path.setText(lib_path)
            
            # 更新标签过滤器
            self._update_tag_filter()
            
            # 显示图片
            self._display_database_images()
            
            # 更新数据库状态
            stats = image_processor.get_image_stats()
            if stats:
                self.db_status_label.setText(
                    f"数据库状态: {stats['total']} 张图片，来自 {stats['ppt_count']} 个PPT"
                )
            
        except Exception as e:
            print(f"加载数据库状态时出错: {str(e)}")

    def init_ui(self):
        """初始化PPT图片数据库标签页的UI"""
        # 创建水平分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板：源管理和设置
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 1. Source PPT文件源管理区域
        source_group = QGroupBox("PPT文件源")
        source_layout = QVBoxLayout()
        
        # PPT源列表
        self.source_table = QTableWidget()
        self.source_table.setColumnCount(2)
        self.source_table.setHorizontalHeaderLabels(["路径", "状态"])
        self.source_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.source_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        
        # 添加/删除源的按钮
        source_btn_layout = QHBoxLayout()
        add_source_btn = QPushButton("添加PPT文件夹")
        add_source_btn.clicked.connect(self._add_ppt_source)
        remove_source_btn = QPushButton("删除选中")
        remove_source_btn.clicked.connect(self._remove_ppt_source)
        scan_source_btn = QPushButton("扫描更新")
        scan_source_btn.clicked.connect(self._scan_ppt_source)
        
        source_btn_layout.addWidget(add_source_btn)
        source_btn_layout.addWidget(remove_source_btn)
        source_btn_layout.addWidget(scan_source_btn)
        source_btn_layout.addStretch()
        
        source_layout.addWidget(self.source_table)
        source_layout.addLayout(source_btn_layout)
        source_group.setLayout(source_layout)
        
        # 2. 图片库设置和操作区域
        settings_group = QGroupBox("图片库设置")
        settings_layout = QVBoxLayout()
        
        # 图片库路径设置
        path_layout = QHBoxLayout()
        self.image_lib_path = QLineEdit()
        self.image_lib_path.setPlaceholderText("选择高质量图片存位置")
        image_lib_browse_btn = QPushButton("浏览")
        image_lib_browse_btn.clicked.connect(self._browse_image_lib)
        
        path_layout.addWidget(QLabel("图片库位置:"))
        path_layout.addWidget(self.image_lib_path)
        path_layout.addWidget(image_lib_browse_btn)
        
        # 操作按
        action_layout = QHBoxLayout()
        extract_btn = QPushButton("提取并建立索引")
        extract_btn.clicked.connect(self._extract_and_index)
        rebuild_db_btn = QPushButton("重建数据库")
        rebuild_db_btn.clicked.connect(self._rebuild_database)
        
        action_layout.addWidget(extract_btn)
        action_layout.addWidget(rebuild_db_btn)
        action_layout.addStretch()
        
        # 数据库状态显示
        self.db_status_label = QLabel("数据库状态: 未初始化")
        
        settings_layout.addLayout(path_layout)
        settings_layout.addLayout(action_layout)
        settings_layout.addWidget(self.db_status_label)
        settings_group.setLayout(settings_layout)
        
        # 添加到左侧面板
        left_layout.addWidget(source_group)
        left_layout.addWidget(settings_group)
        left_layout.addStretch()
        
        # 右侧面板：图片显示区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 工具栏：搜索和标签过滤
        toolbar = QHBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.image_search = QLineEdit()
        self.image_search.setPlaceholderText("搜索图片...")
        self.image_search.textChanged.connect(self._filter_images)
        search_layout.addWidget(self.image_search)
        
        # 标签过滤下拉框
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("所有标签")
        self.tag_filter.currentTextChanged.connect(self._filter_images)
        
        # 设置下拉框样式
        self.tag_filter.setMinimumWidth(200)
        self.tag_filter.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.tag_filter.setMaxVisibleItems(20)
        
        # 设置下拉框字体
        font = self.tag_filter.font()
        font.setPointSize(10)
        self.tag_filter.setFont(font)
        
        # 添加到布局
        search_layout.addWidget(self.tag_filter)
        
        # 标签匹配模式
        self.match_all_tags = QCheckBox("匹配所有标签")
        self.match_all_tags.setChecked(True)
        self.match_all_tags.stateChanged.connect(self._filter_images)
        search_layout.addWidget(self.match_all_tags)
        
        toolbar.addLayout(search_layout)
        toolbar.addStretch()
        
        # 标签管理按钮
        tag_manage_btn = QPushButton("标签管理")
        tag_manage_btn.clicked.connect(self._show_tag_manager)
        toolbar.addWidget(tag_manage_btn)
        
        # 批量处理按钮
        batch_tag_btn = QPushButton("批量标签识别")
        batch_tag_btn.clicked.connect(self._batch_process_tags)
        toolbar.addWidget(batch_tag_btn)
        
        right_layout.addLayout(toolbar)
        
        # 图片网格视图
        self.image_grid = QListWidget()
        self.image_grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_grid.setIconSize(QSize(200, 200))
        self.image_grid.setSpacing(10)
        self.image_grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_grid.customContextMenuRequested.connect(self._show_image_context_menu)
        
        right_layout.addWidget(self.image_grid)
        
        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)  # 左侧面板占比
        splitter.setStretchFactor(1, 2)  # 右侧面板占比
        
        # 添加分割器到主布局
        self.layout.addWidget(splitter)
        
        # 进度条（默认隐藏）
        self.image_progress_bar = QProgressBar()
        self.image_progress_bar.setVisible(False)
        self.layout.addWidget(self.image_progress_bar)
        
        # 添加滚动加载支持
        self.image_grid.verticalScrollBar().valueChanged.connect(self._check_scroll_position)

    def _add_ppt_source(self):
        """添加PPT文件源文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "择PPT文件夹")
        if folder_path:
            # 添加到表格
            row = self.source_table.rowCount()
            self.source_table.insertRow(row)
            self.source_table.setItem(row, 0, QTableWidgetItem(folder_path))
            self.source_table.setItem(row, 1, QTableWidgetItem("未索引"))
            
            # 保存到数据库
            image_processor = self.ppt_processor.get_image_processor()
            image_processor.add_ppt_source(folder_path)

    def _remove_ppt_source(self):
        """删除选中的PPT文件源"""
        selected_rows = set(item.row() for item in self.source_table.selectedItems())
        if not selected_rows:
            QMessageBox.information(self, "提示", "请选择要删除的文件夹")
            return
        
        # 从后向前删除行，避免索引变化
        for row in sorted(selected_rows, reverse=True):
            self.source_table.removeRow(row)

    def _scan_ppt_source(self):
        """扫描并更新PPT文件源"""
        if self.source_table.rowCount() == 0:
            QMessageBox.information(self, "提示", "请先添加PPT文件夹")
            return
        
        try:
            # 显示进度条
            self.image_progress_bar.setVisible(True)
            self.image_progress_bar.setMaximum(self.source_table.rowCount())
            self.image_progress_bar.setValue(0)
            
            total_ppts = 0
            for row in range(self.source_table.rowCount()):
                folder_path = self.source_table.item(row, 0).text()
                
                # 统计PPT文件数量
                ppt_count = sum(1 for f in Path(folder_path).rglob('*.ppt*')
                              if not f.name.startswith('~$'))
                
                # 更新状态
                status_item = QTableWidgetItem(f"已找到 {ppt_count} 个PPT")
                self.source_table.setItem(row, 1, status_item)
                
                total_ppts += ppt_count
                self.image_progress_bar.setValue(row + 1)
            
            # 更新数据库状态
            self.db_status_label.setText(f"数据库状态: 共发现 {total_ppts} 个PPT文件")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"扫描文件夹时出错：{str(e)}")
        finally:
            self.image_progress_bar.setVisible(False)

    def _browse_image_lib(self):
        """选择图片库位置"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片库位置")
        if folder_path:
            self.image_lib_path.setText(folder_path)
            # 保存设置
            image_processor = self.ppt_processor.get_image_processor()
            image_processor.save_setting('image_lib_path', folder_path)

    def _extract_and_index(self):
        """提取图片并建立索引"""
        if not self.image_lib_path.text():
            QMessageBox.warning(self, "警告", "请先选择图片库位置")
            return
        
        if self.source_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请先添加PPT文件夹")
            return
        
        try:
            image_processor = self.ppt_processor.get_image_processor()
            
            # 示进度条
            self.image_progress_bar.setVisible(True)
            total_images = 0
            total_ppts = 0
            
            # 处理每个源文件夹
            for row in range(self.source_table.rowCount()):
                folder_path = self.source_table.item(row, 0).text()
                
                # 统计PPT文件数量
                ppt_files = list(Path(folder_path).rglob('*.ppt*'))
                ppt_files = [f for f in ppt_files if not f.name.startswith('~$')]
                
                # 设置进度最大值（每个PPT文100个单位）
                self.image_progress_bar.setMaximum(len(ppt_files) * 100)
                self.image_progress_bar.setValue(0)
                
                # 遍历所有PPT文件
                for ppt_idx, ppt_file in enumerate(ppt_files, 1):
                    try:
                        # 更新状态
                        self.source_table.setItem(
                            row, 1,
                            QTableWidgetItem(f"正在处理: {ppt_file.name}")
                        )
                        
                        def update_progress(current, total, message):
                            # 计算当前PPT的进度（0-100）
                            progress = int((current / total) * 100)
                            # 计算总进度
                            total_progress = (ppt_idx - 1) * 100 + progress
                            self.image_progress_bar.setValue(total_progress)
                            
                            self.source_table.setItem(
                                row, 1,
                                QTableWidgetItem(f"{message} - {ppt_file.name}")
                            )
                            QApplication.processEvents()
                        
                        # 提取图片
                        extracted = image_processor.extract_background_images(
                            str(ppt_file),
                            self.image_lib_path.text(),
                            progress_callback=update_progress
                        )
                        
                        total_images += len(extracted)
                        total_ppts += 1
                        
                    except Exception as e:
                        print(f"处理 {ppt_file} 时出错: {str(e)}")
                        continue
                    
                    # 更新进度条到当前PPT的100%
                    self.image_progress_bar.setValue(ppt_idx * 100)
                    QApplication.processEvents()
                
                # 更新最状态
                self.source_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"已处理 {total_ppts} 个PPT")
                )
            
            # 更新数据库状态
            self.db_status_label.setText(
                f"数据库状态: 已处理 {total_ppts} 个PPT，提取 {total_images} 张图片"
            )
            
            # 刷新图片显示
            self._display_database_images()
            
            QMessageBox.information(
                self,
                "完成",
                f"索引建立完成\n处理了 {total_ppts} 个PPT文件\n提取了 {total_images} 张图片"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理时出错：{str(e)}")
        finally:
            self.image_progress_bar.setVisible(False)

    def _rebuild_database(self):
        """重图片数据"""
        if not self.image_lib_path.text():
            QMessageBox.warning(self, "警告", "请先选择图片库位置")
            return
        
        reply = QMessageBox.question(
            self,
            "确认重建",
            "重建数据库将清除所有现有索引，确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 初始化图处理器
                image_processor = self.ppt_processor.get_image_processor()
                
                # 重新建立索引
                self._extract_and_index()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重建数据库时出错：{str(e)}")

    def _filter_images(self):
        """根据搜索文本和标���过滤图片"""
        try:
            search_text = self.image_search.text().lower()
            selected_tag = self.tag_filter.currentText().strip()
            
            # 忽略分隔符类别标题
            if selected_tag.startswith('─') or selected_tag.startswith('【'):
                return
            
            # 获取图片处理器
            image_processor = self.ppt_processor.get_image_processor()
            
            # 收集要搜索的标签
            search_tags = set()
            
            # 添加下拉框选中的标签
            if selected_tag != "所有标签":
                search_tags.add(selected_tag)
            
            # 从搜索文本中提取标签
            if search_text:
                # 获取所有标签
                all_tags = {tag['name'].lower(): tag['name'] for tag in image_processor.get_all_tags()}
                # 检查搜索文本是否匹配任何标签
                for tag_name_lower, tag_name in all_tags.items():
                    if tag_name_lower in search_text:
                        search_tags.add(tag_name)
            
            # 搜索图片
            if search_tags:
                print(f"搜索标签: {search_tags}")
                images = image_processor.search_images_by_tags(
                    tuple(sorted(search_tags)),  # 转换为元组以支持缓存
                    match_all=self.match_all_tags.isChecked()
                )
                
                # 如果有文本搜索，进一步过滤
                if search_text and not any(tag.lower() in search_text for tag in search_tags):
                    images = [img for img in images if search_text in img['name'].lower()]
            else:
                # 如果没有标签，则按文本搜索
                images = image_processor.get_all_images()
                if search_text:
                    images = [img for img in images if search_text in img['name'].lower()]
            
            # 重置分页状态
            self.current_page = 0
            self.has_more = True
            
            # 显示结果
            self._display_database_images(images)
            
            # 更新状态
            status_text = f"显示 {len(images)} 张图片"
            if search_tags:
                status_text += f" (标签: {', '.join(search_tags)})"
            self.db_status_label.setText(status_text)
            
        except Exception as e:
            print(f"过滤图片失: {str(e)}")
            import traceback
            traceback.print_exc()

    def _toggle_view_mode(self):
        """切换图显示模式（网格/列表）"""
        current_mode = self.image_grid.viewMode()
        if current_mode == QListWidget.ViewMode.IconMode:
            self.image_grid.setViewMode(QListWidget.ViewMode.ListMode)
            self.image_grid.setSpacing(0)
        else:
            self.image_grid.setViewMode(QListWidget.ViewMode.IconMode)
            self.image_grid.setSpacing(10)

    def _show_image_context_menu(self, pos):
        """显示图片右键菜单"""
        menu = QMenu(self)
        
        item = self.image_grid.itemAt(pos)
        if item:
            image_info = item.data(Qt.ItemDataRole.UserRole)
            if image_info and 'hash' in image_info:
                # 获取所有使用该图片的PPT
                image_processor = self.ppt_processor.get_image_processor()
                mappings = image_processor.get_image_ppt_mappings(image_info['hash'])
                
                # 按PPT文件分组映射信息
                ppt_groups = {}
                for mapping in mappings:
                    ppt_path = mapping['ppt_path']
                    if ppt_path not in ppt_groups:
                        ppt_groups[ppt_path] = {
                            'name': mapping['ppt_name'],
                            'slides': []
                        }
                    ppt_groups[ppt_path]['slides'].append({
                        'slide': mapping['slide'],
                        'shape': mapping['shape']
                    })
                
                # 添加PPT查找菜单
                if ppt_groups:
                    ppt_menu = menu.addMenu("查找使用此图片的PPT")
                    for ppt_path, info in ppt_groups.items():
                        # 创建PPT子菜单
                        ppt_submenu = ppt_menu.addMenu(info['name'])
                        
                        # 添加"打开PPT文件"操作
                        open_action = ppt_submenu.addAction("打开PPT文件")
                        open_action.triggered.connect(
                            lambda checked, p=ppt_path: self._open_ppt_file(p)
                        )
                        
                        # 添加分隔线
                        ppt_submenu.addSeparator()
                        
                        # 添加页面信息
                        if info['slides']:
                            # 按页码排序
                            sorted_slides = sorted(info['slides'], key=lambda x: x['slide'])
                            for slide_info in sorted_slides:
                                slide_action = ppt_submenu.addAction(
                                    f"第 {slide_info['slide']} 页"
                                )
                                # 这里可以添加跳转到具体页面的功能
                
                # 添加其他菜单项
                menu.addSeparator()
                
                find_ppt_action = menu.addAction("打开所在文件夹")
                find_ppt_action.triggered.connect(lambda: self._open_image_folder(item))
                
                copy_action = menu.addAction("复制图片")
                copy_action.triggered.connect(lambda: self._copy_image(item))
                
                menu.exec(self.image_grid.mapToGlobal(pos))

    def _find_source_ppt(self, item):
        """查找图片所在的PPT文件"""
        if not item:
            return
        
        image_info = item.data(Qt.ItemDataRole.UserRole)
        if not image_info or 'ppt_path' not in image_info:
            return
        
        ppt_path = image_info['ppt_path']
        if not Path(ppt_path).exists():
            QMessageBox.warning(self, "警告", "原PPT文件已不存在")
            return
        
        # 打开文件所在文夹并选文件
        if os.name == 'nt':  # Windows
            os.system(f'explorer /select,"{ppt_path}"')
        else:  # macOS 和 Linux
            os.system(f'open -R "{ppt_path}"')

    def _open_image_folder(self, item):
        """打开图片所在文件夹"""
        if not item:
            return
        
        image_info = item.data(Qt.ItemDataRole.UserRole)
        if not image_info or 'path' not in image_info:
            return
        
        image_path = image_info['path']
        if not Path(image_path).exists():
            QMessageBox.warning(self, "警告", "图片文件已不存在")
            return
        
        # 打开文件所在文件夹
        if os.name == 'nt':  # Windows
            os.system(f'explorer /select,"{image_path}"')
        else:  # macOS 和 Linux
            os.system(f'open -R "{image_path}"')

    def _copy_image(self, item):
        """复制图片到剪贴板，保留透明通道"""
        if not item:
            return
        
        image_info = item.data(Qt.ItemDataRole.UserRole)
        if not image_info or 'path' not in image_info:
            return
        
        image_path = image_info['path']
        if not Path(image_path).exists():
            QMessageBox.warning(self, "警告", "图片文件已不存在")
            return
        
        try:
            # 使用PIL打开图片以检查格式
            with Image.open(image_path) as pil_img:
                # 如果是PNG且有透明通道
                if pil_img.format == 'PNG' and pil_img.mode == 'RGBA':
                    # 将图片保存到内存中
                    output = io.BytesIO()
                    pil_img.save(output, 'PNG')
                    data = output.getvalue()
                    output.close()
                    
                    # 打开剪贴板
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32con.CF_DIB, data[8:])
                        png_format = win32clipboard.RegisterClipboardFormat('PNG')
                        if png_format:
                            win32clipboard.SetClipboardData(png_format, data)
                    finally:
                        win32clipboard.CloseClipboard()
                    return
                
                # 对于其他格式的图片，使用常规方式复制
                qimage = QImage(image_path)
                QApplication.clipboard().setImage(qimage)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"制图片时出错：{str(e)}")

    def _update_load_progress(self, current: int, total: int):
        """更新加载进度"""
        if self.image_progress_bar.isVisible():
            self.image_progress_bar.setValue(current)
            if current >= total:
                self.image_progress_bar.setVisible(False)

    def _display_database_images(self, images=None):
        """显示数据库中的图片"""
        try:
            # 停止现有的加载线程
            if self.image_loader and self.image_loader.isRunning():
                self.image_loader.stop()
                self.image_loader.deleteLater()
                self.image_loader = None
            
            # 清空当前显示
            self.image_grid.clear()
            self.loaded_images.clear()
            
            if images is None:
                # 如果没有指定图片列表，获取所有图片
                image_processor = self.ppt_processor.get_image_processor()
                images = image_processor.get_all_images()
            
            # 保存完整的图片列表
            self.all_images = images
            self.total_images = len(images)
            
            # 显示第一页的图片
            self.current_page = 0
            self.has_more = self.total_images > self.page_size
            
            # 加载第一页
            self._load_page()
            
        except Exception as e:
            print(f"显示图片失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def _load_page(self):
        """加载当前页的图片"""
        try:
            # 停止现有的加载线程
            self._cleanup_loader()
            
            # 计算当前页的图片范围
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, self.total_images)
            current_images = self.all_images[start_idx:end_idx]
            
            # 创建并启动图片加载线程
            self.image_loader = ImageLoader(
                self.ppt_processor.get_image_processor(),
                current_images
            )
            
            # 连接信号
            self.image_loader.image_loaded.connect(self._add_image_item)
            self.image_loader.batch_finished.connect(self._on_batch_finished)
            self.image_loader.progress_updated.connect(self._update_load_progress)
            
            # 启动加载
            self.image_loader.start()
            
            # 更新状态
            self.db_status_label.setText(
                f"显示 {start_idx + 1}-{end_idx} / {self.total_images} 张图片"
            )
            
        except Exception as e:
            print(f"加载页面失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def _on_batch_finished(self):
        """一批图片加载完成的处理"""
        self.is_loading = False
        self.image_grid.update()
        
        # 如果窗口还有空间，继续加载下一批
        if (self.image_grid.count() < self.page_size and 
            self.has_more and not self.is_loading):
            QTimer.singleShot(100, self._load_more_images)

    def _check_scroll_position(self):
        """检查滚动位置，决定是否加载下一页"""
        scrollbar = self.image_grid.verticalScrollBar()
        if (not self.is_loading and self.has_more and 
            scrollbar.value() >= scrollbar.maximum() - 100):  # 接近底部时加载
            self._load_more_images()

    def _load_more_images(self):
        """加载更多图片"""
        if self.is_loading or not self.has_more:
            return
            
        self.is_loading = True
        
        try:
            # 使用已经过滤好的图片列表
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.all_images))
            current_images = self.all_images[start_idx:end_idx]
            
            if not current_images:
                self.has_more = False
                self.is_loading = False
                return
            
            # 创建并启动加载线程
            self.image_loader = ImageLoader(
                self.ppt_processor.get_image_processor(),
                current_images
            )
            self.image_loader.image_loaded.connect(self._add_image_item)
            self.image_loader.progress_updated.connect(self._update_load_progress)
            self.image_loader.batch_finished.connect(self._on_batch_finished)
            self.image_loader.start()
            
            self.current_page += 1
            self.has_more = end_idx < len(self.all_images)
            
            # 更新状态
            self.db_status_label.setText(
                f"显示 {start_idx + 1}-{end_idx} / {len(self.all_images)} 张图片"
            )
            
        except Exception as e:
            print(f"加载更多图片时出错: {str(e)}")
            self.is_loading = False

    def _add_image_item(self, img_info: dict, thumb_path: str):
        """添加单个图片项"""
        if img_info['hash'] in self.loaded_images:
            return
            
        try:
            # 创建透明背景的图标
            if thumb_path.lower().endswith('.png'):
                # 使用QImage直接加载PNG
                qimage = QImage(thumb_path)
                if qimage.format() != QImage.Format.Format_ARGB32:
                    qimage = qimage.convertToFormat(QImage.Format.Format_ARGB32)
                pixmap = QPixmap.fromImage(qimage)
            else:
                pixmap = QPixmap(thumb_path)
            
            if not pixmap.isNull():
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
                
                item = QListWidgetItem()
                item.setIcon(QIcon(transparent_pixmap))
                item.setSizeHint(QSize(220, 240))
                
                # 获取图片的标签
                image_processor = self.ppt_processor.get_image_processor()
                tags = image_processor.get_image_tags(img_info['hash'])
                
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
                    f"使用于 {img_info.get('ref_count', 0)} 个PPT中",
                    f"提取时间: {img_info['extract_date']}"
                ]
                if tags:
                    tooltip.append("\n标签:")
                    for tag in sorted(tags, key=lambda x: x['confidence'], reverse=True):
                        tooltip.append(f"- {tag['name']} ({tag['confidence']:.2f})")
                
                item.setToolTip("\n".join(tooltip))
                
                item.setData(Qt.ItemDataRole.UserRole, img_info)
                self.image_grid.addItem(item)
                
                self.loaded_images.add(img_info['hash'])
                
        except Exception as e:
            print(f"添加图片项时出错: {str(e)}")

    def _update_progress(self, current: int, total: int):
        """更新进度条"""
        self.image_progress_bar.setMaximum(total)
        self.image_progress_bar.setValue(current)
        
        # 更新状态
        self.db_status_label.setText(
            f"数据库状态: 已加载 {len(self.loaded_images)} / {total} 张图片"
        )

    def _open_ppt_file(self, ppt_path: str):
        """打开PPT文件"""
        if not os.path.exists(ppt_path):
            QMessageBox.warning(self, "警告", "PPT文件已不存在")
            return
        
        if os.name == 'nt':  # Windows
            os.system(f'explorer /select,"{ppt_path}"')
        else:  # macOS 和 Linux
            os.system(f'open -R "{ppt_path}"')

    def _handle_key_press(self, event):
        """处理键盘事件"""
        # Ctrl+C: 复制选中的图片
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            selected_items = self.image_grid.selectedItems()
            if selected_items:
                self._copy_image(selected_items[0])
                return
            
        # 调用父类的键盘事件处理
        QListWidget.keyPressEvent(self.image_grid, event)

    def _show_tag_manager(self):
        """显示标签管理对话框"""
        dialog = TagManagerDialog(self.ppt_processor.get_image_processor(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新标签过滤器
            self._update_tag_filter()
            # 刷新图片显示
            self._filter_images()

    def _update_tag_filter(self):
        """更新标签过滤下拉框"""
        try:
            image_processor = self.ppt_processor.get_image_processor()
            tags = image_processor.get_all_tags()
            
            current = self.tag_filter.currentText()
            self.tag_filter.clear()
            self.tag_filter.addItem("所有标签")
            
            # 按类别分组添加标签
            categories = {}
            for tag in tags:
                cat = tag['category'] or "未分类"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(tag['name'])
            
            # 添加标签（不使用分隔符和类别标题）
            for category, tag_names in sorted(categories.items()):
                for name in sorted(tag_names):
                    self.tag_filter.addItem(name)
            
            # 恢复之前的选择
            index = self.tag_filter.findText(current)
            if index >= 0:
                self.tag_filter.setCurrentIndex(index)
            
            # 调整下拉框宽度以适应内容
            self.tag_filter.adjustSize()
            
        except Exception as e:
            print(f"更新标签过滤器失败: {str(e)}")

    def _batch_process_tags(self):
        """批量处理图片标签"""
        try:
            image_processor = self.ppt_processor.get_image_processor()
            if not image_processor.clip_available:
                QMessageBox.warning(
                    self,
                    "功能不可",
                    "标签识别功能需要安装额外的库。\n"
                    "请运行: pip install transformers torch torchvision"
                )
                return
            
            reply = QMessageBox.question(
                self,
                "确认",
                "是否要对所有图片进行标签识别？这可能需要一些时间。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 显示进度条
                self.image_progress_bar.setVisible(True)
                self.image_progress_bar.setValue(0)
                
                # 创建进度对话框
                progress_dialog = QProgressDialog("正在处理图片标签...", "取消", 0, 100, self)
                progress_dialog.setWindowTitle("标签识别")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setMinimumDuration(0)
                progress_dialog.setAutoClose(True)
                
                def update_progress(current, total):
                    if progress_dialog.wasCanceled():
                        return False
                    
                    progress = int((current / total) * 100)
                    progress_dialog.setValue(progress)
                    progress_dialog.setLabelText(
                        f"正在处理标签: {current}/{total}\n"
                        f"完成进度: {progress}%"
                    )
                    QApplication.processEvents()
                    return True
                
                # 执行批量处理
                processed = image_processor.batch_process_tags(
                    confidence_threshold=0.5,
                    progress_callback=update_progress
                )
                
                # 关闭进度对话框
                progress_dialog.close()
                
                # 显示结果
                if processed > 0:
                    QMessageBox.information(
                        self,
                        "完成",
                        f"标签处理完成，共处理 {processed} 张图片"
                    )
                    # 刷新标签过滤器
                    self._update_tag_filter()
                    # 刷新显示
                    self._filter_images()
                else:
                    QMessageBox.warning(
                        self,
                        "提示",
                        "没有处理任何图片，请确保已添加标签"
                    )
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量处理标签失败：{str(e)}")
        finally:
            self.image_progress_bar.setVisible(False)