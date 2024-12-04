from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QGridLayout,
    QSplitter, QListWidget, QListWidgetItem, QWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

class ImageDBUI:
    """UI组件管理"""
    def __init__(self):
        # 存储UI组件的引用
        self.image_grid = None
        self.image_search = None
        self.tag_filter = None
        self.match_all_tags = None
        self.source_table = None
        self.image_lib_path = None
        self.image_progress_bar = None
        self.db_status_label = None
        self.add_source_btn = None
        self.remove_source_btn = None
        self.scan_source_btn = None
        self.image_lib_browse_btn = None
        self.extract_btn = None
        self.rebuild_db_btn = None
        self.tag_manage_btn = None
        self.batch_tag_btn = None

    def setup_ui(self, tab):
        """初始化UI"""
        # 创建水平分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板
        left_panel = self._create_left_panel()
        
        # 右侧面板
        right_panel = self._create_right_panel()
        
        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)  # 左侧面板占比
        splitter.setStretchFactor(1, 2)  # 右侧面板占比
        
        # 添加分割器到主布局
        tab.layout.addWidget(splitter)
        
        # 进度条（默认隐藏）
        self.image_progress_bar = QProgressBar()
        self.image_progress_bar.setVisible(False)
        tab.layout.addWidget(self.image_progress_bar)

    def _create_left_panel(self):
        """创建左侧面板"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 1. Source PPT文件源管理区域
        source_group = self._create_source_group()
        
        # 2. 图片库设置和操作区域
        settings_group = self._create_settings_group()
        
        # 添加到左侧面板
        left_layout.addWidget(source_group)
        left_layout.addWidget(settings_group)
        left_layout.addStretch()
        
        return left_panel

    def _create_source_group(self):
        """创建源管理组"""
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
        self.add_source_btn = QPushButton("添加PPT文件夹")
        self.remove_source_btn = QPushButton("删除选中")
        self.scan_source_btn = QPushButton("扫描更新")
        
        source_btn_layout.addWidget(self.add_source_btn)
        source_btn_layout.addWidget(self.remove_source_btn)
        source_btn_layout.addWidget(self.scan_source_btn)
        source_btn_layout.addStretch()
        
        source_layout.addWidget(self.source_table)
        source_layout.addLayout(source_btn_layout)
        source_group.setLayout(source_layout)
        
        return source_group

    def _create_settings_group(self):
        """创建设置组"""
        settings_group = QGroupBox("图片库设置")
        settings_layout = QVBoxLayout()
        
        # 图片库路径设置
        path_layout = QHBoxLayout()
        self.image_lib_path = QLineEdit()
        self.image_lib_path.setPlaceholderText("选择高质量图片存储位置")
        self.image_lib_browse_btn = QPushButton("浏览")
        
        path_layout.addWidget(QLabel("图片库位置:"))
        path_layout.addWidget(self.image_lib_path)
        path_layout.addWidget(self.image_lib_browse_btn)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        self.extract_btn = QPushButton("提取并建立索引")
        self.rebuild_db_btn = QPushButton("重建数据库")
        
        action_layout.addWidget(self.extract_btn)
        action_layout.addWidget(self.rebuild_db_btn)
        action_layout.addStretch()
        
        # 数据库状态显示
        self.db_status_label = QLabel("数据库状态: 未初始化")
        
        settings_layout.addLayout(path_layout)
        settings_layout.addLayout(action_layout)
        settings_layout.addWidget(self.db_status_label)
        settings_group.setLayout(settings_layout)
        
        return settings_group

    def _create_right_panel(self):
        """创建右侧面板"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 工具栏：搜索和标签过滤
        toolbar = self._create_toolbar()
        right_layout.addLayout(toolbar)
        
        # 图片网格视图
        self.image_grid = QListWidget()
        self.image_grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_grid.setIconSize(QSize(200, 200))
        self.image_grid.setSpacing(10)
        self.image_grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        right_layout.addWidget(self.image_grid)
        
        return right_panel

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QHBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.image_search = QLineEdit()
        self.image_search.setPlaceholderText('搜索图片... (使用双引号标记标签，如: "car interior" "red")')
        search_layout.addWidget(self.image_search)
        
        # 标签过滤下拉框
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("所有标签")
        
        # 设置下拉框样式
        self.tag_filter.setMinimumWidth(200)
        self.tag_filter.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.tag_filter.setMaxVisibleItems(20)
        
        # 设置下拉框字体
        font = self.tag_filter.font()
        font.setPointSize(10)
        self.tag_filter.setFont(font)
        
        search_layout.addWidget(self.tag_filter)
        
        # 标签匹配模式
        self.match_all_tags = QCheckBox("匹配所有标签")
        self.match_all_tags.setChecked(True)
        search_layout.addWidget(self.match_all_tags)
        
        toolbar.addLayout(search_layout)
        toolbar.addStretch()
        
        # 标签管理按钮
        self.tag_manage_btn = QPushButton("标签管理")
        toolbar.addWidget(self.tag_manage_btn)
        
        # 批量处理按钮
        self.batch_tag_btn = QPushButton("批量标签识别")
        toolbar.addWidget(self.batch_tag_btn)
        
        return toolbar

    def get_components(self):
        """获取UI组件引用"""
        return {
            'image_grid': self.image_grid,
            'image_search': self.image_search,
            'tag_filter': self.tag_filter,
            'match_all_tags': self.match_all_tags,
            'source_table': self.source_table,
            'image_lib_path': self.image_lib_path,
            'image_progress_bar': self.image_progress_bar,
            'db_status_label': self.db_status_label,
            'add_source_btn': self.add_source_btn,
            'remove_source_btn': self.remove_source_btn,
            'scan_source_btn': self.scan_source_btn,
            'image_lib_browse_btn': self.image_lib_browse_btn,
            'extract_btn': self.extract_btn,
            'rebuild_db_btn': self.rebuild_db_btn,
            'tag_manage_btn': self.tag_manage_btn,
            'batch_tag_btn': self.batch_tag_btn
        }