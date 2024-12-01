from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QGridLayout,
    QSplitter, QListWidget, QListWidgetItem, QWidget, QMenu, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtWidgets import QApplication
import os
import threading
import subprocess
from pathlib import Path
from .base_tab import BaseTab

class ImageDBTab(BaseTab):
    def __init__(self, ppt_processor, parent=None):
        self.ppt_processor = ppt_processor
        super().__init__(parent)
        # 初始化完成后显示图片
        QTimer.singleShot(100, self._display_database_images)
    
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
        self.image_lib_path.setPlaceholderText("选择高质量图片存储位置")
        image_lib_browse_btn = QPushButton("浏览")
        image_lib_browse_btn.clicked.connect(self._browse_image_lib)
        
        path_layout.addWidget(QLabel("图片库位置:"))
        path_layout.addWidget(self.image_lib_path)
        path_layout.addWidget(image_lib_browse_btn)
        
        # 操作按钮
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
        
        # 图片过滤和搜索工具栏
        toolbar = QHBoxLayout()
        self.image_search = QLineEdit()
        self.image_search.setPlaceholderText("搜索图片...")
        self.image_search.textChanged.connect(self._filter_images)
        
        view_mode_btn = QPushButton("切换视图")
        view_mode_btn.clicked.connect(self._toggle_view_mode)
        
        toolbar.addWidget(self.image_search)
        toolbar.addWidget(view_mode_btn)
        
        # 图片网格视图
        self.image_grid = QListWidget()
        self.image_grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_grid.setIconSize(QSize(200, 200))
        self.image_grid.setSpacing(10)
        self.image_grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_grid.customContextMenuRequested.connect(self._show_image_context_menu)
        
        right_layout.addLayout(toolbar)
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

    def _add_ppt_source(self):
        """添加PPT文件源文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择PPT文件夹")
        if folder_path:
            # 添加新行
            row = self.source_table.rowCount()
            self.source_table.insertRow(row)
            
            # 设置路径
            path_item = QTableWidgetItem(folder_path)
            self.source_table.setItem(row, 0, path_item)
            
            # 设置状态为"未索引"
            status_item = QTableWidgetItem("未索引")
            self.source_table.setItem(row, 1, status_item)

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

    def _extract_and_index(self):
        """提取图片并建立索引"""
        if not self.image_lib_path.text():
            QMessageBox.warning(self, "警告", "请先选择图片库位置")
            return
        
        if self.source_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请先添加PPT文件夹")
            return
        
        try:
            # 初始化图片处理器
            image_processor = self.ppt_processor.get_image_processor()
            
            # 显示进度条
            self.image_progress_bar.setVisible(True)
            self.image_progress_bar.setMaximum(0)  # 显示忙碌状态
            
            total_images = 0
            total_ppts = 0
            
            # 处理每个源文件夹
            for row in range(self.source_table.rowCount()):
                folder_path = self.source_table.item(row, 0).text()
                
                # 遍历所有PPT文件
                for ppt_file in Path(folder_path).rglob('*.ppt*'):
                    if ppt_file.name.startswith('~$'):
                        continue
                    
                    try:
                        # 提取图片
                        extracted = image_processor.extract_background_images(
                            str(ppt_file),
                            self.image_lib_path.text()
                        )
                        total_images += len(extracted)
                        total_ppts += 1
                        
                        # 更新状态
                        self.source_table.setItem(
                            row, 1,
                            QTableWidgetItem(f"已处理 {total_ppts} 个PPT")
                        )
                        QApplication.processEvents()
                        
                    except Exception as e:
                        print(f"处理 {ppt_file} 时出错: {str(e)}")
                        continue
            
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
        """重建图片数据库"""
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
                # 初始化图片处理器
                image_processor = self.ppt_processor.get_image_processor()
                
                # 重新建立索引
                self._extract_and_index()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重建数据库时出错：{str(e)}")

    def _filter_images(self):
        """根据搜索文本过滤图片"""
        search_text = self.image_search.text().lower()
        
        try:
            # 获取图片处理器
            image_processor = self.ppt_processor.get_image_processor()
            
            # 搜索图片
            images = image_processor.search_images(search_text)
            
            # 显示搜索结果
            self._display_database_images(images)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索图片时出错：{str(e)}")

    def _toggle_view_mode(self):
        """切换图片显示模式（网格/列表）"""
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
        
        # 获取当前选中的图片项
        item = self.image_grid.itemAt(pos)
        if item:
            # 添加菜单项
            find_ppt_action = menu.addAction("查找原PPT文件")
            find_ppt_action.triggered.connect(lambda: self._find_source_ppt(item))
            
            open_folder_action = menu.addAction("打开所在文件夹")
            open_folder_action.triggered.connect(lambda: self._open_image_folder(item))
            
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
        
        # 打开文件所在文件夹并选中文件
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
        """复制图片到剪贴板"""
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
            # 读取图片并复制到剪贴板
            image = QImage(image_path)
            QApplication.clipboard().setImage(image)
            QMessageBox.information(self, "提示", "图片已复制到剪贴板")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制图片时出错：{str(e)}")

    def _display_database_images(self, images=None):
        """显示数据库中的图片"""
        try:
            # 清空当前显示
            self.image_grid.clear()
            
            # 如果没有提供图片列表，获取所有图片
            if images is None:
                image_processor = self.ppt_processor.get_image_processor()
                images = image_processor.get_all_images()
            
            if not images:
                # 如果没有图片，显示提示
                empty_item = QListWidgetItem("暂无图片")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.image_grid.addItem(empty_item)
                return
            
            # 显示图片
            for img_info in images:
                try:
                    if not os.path.exists(img_info['path']):
                        continue
                        
                    # 创建缩略图
                    pixmap = QPixmap(img_info['path'])
                    if not pixmap.isNull():
                        # 创建缩略图（保持宽高比）
                        thumb = pixmap.scaled(
                            200, 200,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        
                        # 创建列表项
                        item = QListWidgetItem()
                        item.setIcon(QIcon(thumb))
                        
                        # 设置项目大小
                        item.setSizeHint(QSize(220, 240))  # 为文本留出空间
                        
                        # 设置工具提示
                        tooltip = (
                            f"文件名: {img_info['name']}\n"
                            f"来源PPT: {img_info['ppt_name']}\n"
                            f"提取时间: {img_info['extract_date']}"
                        )
                        item.setToolTip(tooltip)
                        
                        # 设置显示文本
                        item.setText(f"{img_info['name']}\n来自: {img_info['ppt_name']}")
                        
                        # 存储图片信息
                        item.setData(Qt.ItemDataRole.UserRole, img_info)
                        
                        # 添加到网格
                        self.image_grid.addItem(item)
                        
                except Exception as e:
                    print(f"显示图片时出错: {str(e)}")
                    continue
                
            # 更新状态
            self.db_status_label.setText(f"数据库状态: 显示 {self.image_grid.count()} 张图片")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载图片库时出错：{str(e)}")