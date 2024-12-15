from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QInputDialog, QWidget, QGroupBox, QSplitter, QTextEdit, QMenu, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import Dict, List, Optional
from datetime import datetime

class TagTreeWidget(QTreeWidget):
    """自定义标签树控件"""
    tag_selected = pyqtSignal(dict)  # 发送选中的标签数据
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["标签名称", "层级", "使用次数"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 80)
        
        # 启用拖放
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
    def _show_context_menu(self, position):
        """显示右键菜单"""
        item = self.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        add_child = QAction("添加子标签", self)
        edit_action = QAction("编辑标签", self)
        delete_action = QAction("删除标签", self)
        
        menu.addAction(add_child)
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        
        # 连接信号
        add_child.triggered.connect(lambda: self.parent().add_child_tag(item))
        edit_action.triggered.connect(lambda: self.parent().edit_tag(item))
        delete_action.triggered.connect(lambda: self.parent().remove_tag(item))
        
        menu.exec(self.viewport().mapToGlobal(position))

class TagCategoryTab(QWidget):
    """标签分类标签页"""
    def __init__(self, category_type: str, category_name: str, image_processor, dialog, parent=None):
        super().__init__(parent)
        self.category_type = category_type
        self.category_name = category_name
        self.image_processor = image_processor
        self.tag_manager = image_processor.tag_manager
        self.dialog = dialog  # 保存对话框引用
        
        # 默认提示词
        self.default_prompts = {
            'object': [
                'This image contains {}',
                'A photograph showing {}',
                'The main subject is {}',
                'We can see {} in this image'
            ],
            'scene': [
                'This is a scene of {}',
                'The environment appears to be {}',
                'The location looks like {}',
                'This picture was taken in {}'
            ],
            'style': [
                'The style is {}',
                'This has a {} appearance',
                'The design aesthetic is {}',
                'It features a {} style'
            ],
            'color': [
                'The main color is {}',
                'The dominant color appears to be {}',
                'This image primarily features {} tones',
                'The color scheme is mainly {}'
            ]
        }
        
        layout = QVBoxLayout(self)
        
        # 标签树
        self.tag_tree = TagTreeWidget(self)
        layout.addWidget(self.tag_tree)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加标签")
        self.edit_btn = QPushButton("编辑标签")
        self.remove_btn = QPushButton("删除标签")
        
        self.add_btn.clicked.connect(self.add_tag)
        self.edit_btn.clicked.connect(lambda: self.edit_tag())
        self.remove_btn.clicked.connect(lambda: self.remove_tag())
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.remove_btn)
        layout.addLayout(btn_layout)
    
    def add_tag(self):
        """添加顶级标签"""
        try:
            # 获取分类ID
            categories = self.tag_manager.get_tag_categories()
            category = next((cat for cat in categories if cat['type'] == self.category_type), None)
            if not category:
                raise ValueError(f"找不到分类: {self.category_type}")
            
            category_id = category['id']
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"添加{self.category_name}标签")
            layout = QVBoxLayout(dialog)
            
            # 标签名称
            name_layout = QHBoxLayout()
            name_label = QLabel("标签名称:")
            name_edit = QLineEdit()
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_edit)
            
            # 提示词 - 使用默认提示词模板
            prompt_layout = QVBoxLayout()
            prompt_label = QLabel("提示词(每行一个):")
            prompt_edit = QTextEdit()
            default_prompts = self.default_prompts.get(self.category_type, [])
            prompt_edit.setText('\n'.join(default_prompts))
            prompt_layout.addWidget(prompt_label)
            prompt_layout.addWidget(prompt_edit)
            
            # 置信度阈值
            threshold_layout = QHBoxLayout()
            threshold_label = QLabel("置信度阈值:")
            threshold_edit = QLineEdit()
            threshold_edit.setPlaceholderText("使用分类默认值")
            threshold_layout.addWidget(threshold_label)
            threshold_layout.addWidget(threshold_edit)
            
            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            cancel_btn = QPushButton("取消")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            
            # 添加到主布局
            layout.addLayout(name_layout)
            layout.addLayout(prompt_layout)
            layout.addLayout(threshold_layout)
            layout.addLayout(btn_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    # 添加标签
                    self.tag_manager.add_tag(
                        name=name_edit.text().strip(),
                        category_id=category_id,
                        prompt_words=prompt_edit.toPlainText().replace('\n', ';'),
                        confidence_threshold=(
                            float(threshold_edit.text()) 
                            if threshold_edit.text().strip() 
                            else None
                        )
                    )
                    # 刷新列表
                    self.dialog.load_category_tags(self.category_type)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"添加标签失败：{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取分类ID失败：{str(e)}")
    
    def add_child_tag(self, parent_item: QTreeWidgetItem):
        """添加子标签"""
        parent_tag = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if not parent_tag:
            return
            
        # 显示添加标签对话框
        name, ok = QInputDialog.getText(
            self, "添加子标签", 
            f"请输入 {parent_tag['name']} 的子标签名称:"
        )
        
        if ok and name:
            try:
                # 获取父标签的category_id
                category_id = parent_tag['category_id']
                
                # 添加子标签
                self.tag_manager.add_tag(
                    name=name.strip(),
                    category_id=category_id,  # 使用父标签的category_id
                    parent_id=parent_tag['id']
                )
                # 刷新列表
                self.dialog.load_category_tags(self.category_type)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加子标签失败：{str(e)}")

    def edit_tag(self, item: QTreeWidgetItem = None):
        """编辑标签"""
        try:
            if not item:
                item = self.tag_tree.currentItem()
            if not item:
                QMessageBox.warning(self, "警告", "请选择要编辑的标签")
                return
                
            tag_data = item.data(0, Qt.ItemDataRole.UserRole)
            if not tag_data:
                return
                
            # 显示编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑标签")
            layout = QVBoxLayout(dialog)
            
            # 标签名称
            name_layout = QHBoxLayout()
            name_label = QLabel("标签名称:")
            name_edit = QLineEdit(tag_data['name'])
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_edit)
            
            # 提示词
            prompt_layout = QVBoxLayout()
            prompt_label = QLabel("提示词(每行一个):")
            prompt_edit = QTextEdit()
            if tag_data.get('prompt_words'):
                prompt_edit.setText(tag_data['prompt_words'].replace(';', '\n'))
            prompt_layout.addWidget(prompt_label)
            prompt_layout.addWidget(prompt_edit)
            
            # 置信度阈值
            threshold_layout = QHBoxLayout()
            threshold_label = QLabel("置信度阈值:")
            threshold_edit = QLineEdit(str(tag_data.get('confidence_threshold', '')))
            threshold_edit.setPlaceholderText("使用分类默认值")
            threshold_layout.addWidget(threshold_label)
            threshold_layout.addWidget(threshold_edit)
            
            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            cancel_btn = QPushButton("取消")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            
            # 添加到主布局
            layout.addLayout(name_layout)
            layout.addLayout(prompt_layout)
            layout.addLayout(threshold_layout)
            layout.addLayout(btn_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    # 更新标签
                    self.tag_manager.update_tag(
                        tag_data['id'],
                        name=name_edit.text().strip(),
                        prompt_words=prompt_edit.toPlainText().replace('\n', ';'),
                        confidence_threshold=(
                            float(threshold_edit.text()) 
                            if threshold_edit.text().strip() 
                            else None
                        )
                    )
                    # 刷新列表
                    self.dialog.load_category_tags(self.category_type)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"更新标签失败：{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑标签失败：{str(e)}")
    
    def remove_tag(self, item: QTreeWidgetItem = None):
        """删除标签"""
        try:
            if not item:
                item = self.tag_tree.currentItem()
            if not item:
                QMessageBox.warning(self, "警告", "请选择要删除的标签")
                return
                
            tag_data = item.data(0, Qt.ItemDataRole.UserRole)
            if not tag_data:
                return
                
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除标签 {tag_data['name']} 吗？\n注意：删除标签会同时删除其所有子标签！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # 删除标签
                    self.tag_manager.delete_tag(tag_data['id'])
                    # 刷新列表
                    self.dialog.load_category_tags(self.category_type)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除标签失败：{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除标签失败：{str(e)}")

class TagManagerDialog(QDialog):
    """标签管理对话框"""
    def __init__(self, image_processor, parent=None):
        super().__init__(parent)
        self.image_processor = image_processor
        self.tag_manager = image_processor.tag_manager
        self.setWindowTitle("标签管理")
        self.resize(800, 600)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 添加标签页
        self.category_tabs = {}
        self.load_categories()
        
        # 添加按钮
        btn_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def load_categories(self):
        """加载标签分类"""
        try:
            # 获取所有分类
            categories = self.tag_manager.get_tag_categories()
            
            # 创建分类标签页
            for category in categories:
                tab = TagCategoryTab(
                    category['type'],
                    category['name'],
                    self.image_processor,
                    self
                )
                self.tab_widget.addTab(tab, category['name'])
                self.category_tabs[category['type']] = tab
            
            # 加载每个分类的标签
            for category_type in self.category_tabs:
                self.load_category_tags(category_type)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载标签分类失败：{str(e)}")
    
    def load_category_tags(self, category_type: str):
        """加载指定分类的标签"""
        try:
            if category_type not in self.category_tabs:
                return
                
            tab = self.category_tabs[category_type]
            tree = tab.tag_tree
            tree.clear()
            
            # 获取该分类的标签树
            tag_tree = self.tag_manager.get_tag_tree(category_type)
            
            # 递归添加标签
            def add_tag_items(tags, parent=None):
                for tag in tags:
                    # 创建标签项
                    item = QTreeWidgetItem(parent or tree)
                    item.setText(0, tag['name'])
                    item.setText(1, str(tag['level']))
                    item.setText(2, str(tag.get('usage_count', 0)))
                    item.setData(0, Qt.ItemDataRole.UserRole, tag)
                    
                    # 递归添加子标签
                    if tag.get('children'):
                        add_tag_items(tag['children'], item)
            
            # 添加所有标签
            add_tag_items(tag_tree)
            
            # 展开所有项
            tree.expandAll()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载标签失败：{str(e)}") 