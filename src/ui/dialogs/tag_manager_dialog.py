from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QInputDialog, QWidget, QGroupBox, QListWidget, QSplitter
)
from PyQt6.QtCore import Qt
from typing import Dict, List

class TagManagerDialog(QDialog):
    def __init__(self, image_processor, parent=None):
        super().__init__(parent)
        self.image_processor = image_processor
        self.setWindowTitle("标签管理")
        self.resize(600, 400)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：分类管理
        category_group = QGroupBox("分类管理")
        category_layout = QVBoxLayout()
        
        # 分类列表
        self.category_list = QListWidget()
        self.category_list.itemSelectionChanged.connect(self._on_category_selected)
        category_layout.addWidget(self.category_list)
        
        # 分类操作按钮
        category_btn_layout = QHBoxLayout()
        self.add_category_btn = QPushButton("添加分类")
        self.edit_category_btn = QPushButton("编辑分类")
        self.remove_category_btn = QPushButton("删除分类")
        
        self.add_category_btn.clicked.connect(self._add_category)
        self.edit_category_btn.clicked.connect(self._edit_category)
        self.remove_category_btn.clicked.connect(self._remove_category)
        
        category_btn_layout.addWidget(self.add_category_btn)
        category_btn_layout.addWidget(self.edit_category_btn)
        category_btn_layout.addWidget(self.remove_category_btn)
        category_layout.addLayout(category_btn_layout)
        
        category_group.setLayout(category_layout)
        
        # 右侧：标签管理
        tag_group = QGroupBox("标签管理")
        tag_layout = QVBoxLayout()
        
        # 标签列表
        self.tag_list = QTableWidget()
        self.tag_list.setColumnCount(3)
        self.tag_list.setHorizontalHeaderLabels(["标签名", "分类", "使用次数"])
        self.tag_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tag_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tag_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tag_layout.addWidget(self.tag_list)
        
        # 标签操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加标签")
        self.edit_btn = QPushButton("编辑标签")
        self.remove_btn = QPushButton("删除标签")
        
        self.add_btn.clicked.connect(self._add_tag)
        self.edit_btn.clicked.connect(self._edit_tag)
        self.remove_btn.clicked.connect(self._remove_tag)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.remove_btn)
        tag_layout.addLayout(btn_layout)
        
        tag_group.setLayout(tag_layout)
        
        # 添加到分割器
        splitter.addWidget(category_group)
        splitter.addWidget(tag_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载数据"""
        # 加载分类
        categories = self.image_processor.get_tag_categories()
        self.category_list.clear()
        self.category_list.addItem("所有分类")
        for category in categories:
            self.category_list.addItem(category)
        
        # 加载标签
        self._load_tags()

    def _load_tags(self, category=None):
        """加载标签"""
        tags = self.image_processor.get_all_tags()
        if category and category != "所有分类":
            tags = [tag for tag in tags if tag['category'] == category]
        
        self.tag_list.setRowCount(len(tags))
        for row, tag in enumerate(tags):
            self.tag_list.setItem(row, 0, QTableWidgetItem(tag['name']))
            self.tag_list.setItem(row, 1, QTableWidgetItem(tag['category'] or "未分类"))
            self.tag_list.setItem(row, 2, QTableWidgetItem(str(tag['usage_count'])))

    def _on_category_selected(self):
        """分类选择改变时更新标签列表"""
        items = self.category_list.selectedItems()
        if items:
            category = items[0].text()
            self._load_tags(category)

    def _add_category(self):
        """添加分类"""
        name, ok = QInputDialog.getText(self, "添加分类", "分类名称:")
        if ok and name:
            # 添加到数据库
            self.image_processor.add_tag_category(name)
            # 刷新列表
            self._load_data()

    def _edit_category(self):
        """编辑分类"""
        items = self.category_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "警告", "请选择要编辑的分类")
            return
        
        old_name = items[0].text()
        if old_name == "所有分类":
            QMessageBox.warning(self, "警告", "不能编辑默认分类")
            return
        
        new_name, ok = QInputDialog.getText(self, "编辑分类", "分类名称:", text=old_name)
        if ok and new_name:
            # 更新数据库
            self.image_processor.update_tag_category(old_name, new_name)
            # 刷新列表
            self._load_data()

    def _remove_category(self):
        """删除分类"""
        items = self.category_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "警告", "请选择要删除的分类")
            return
        
        category = items[0].text()
        if category == "所有分类":
            QMessageBox.warning(self, "警告", "不能删除默认分类")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分类 '{category}' 吗？\n该分类下的标签将移至'未分类'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 删除分类
            self.image_processor.delete_tag_category(category)
            # 刷新列表
            self._load_data()
    
    def _add_tag(self):
        """添加标签"""
        try:
            # 获取当前选中的分类
            category = None
            items = self.category_list.selectedItems()
            if items and items[0].text() != "所有分类":
                category = items[0].text()
            
            # 显示添加标签对话框
            name, ok = QInputDialog.getText(self, "添加标签", "标签名称:")
            if ok and name:
                # 添加标签
                self.image_processor.add_tags([{
                    'name': name,
                    'category': category
                }])
                
                # 刷新列表
                self._load_tags(category)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加标签失败：{str(e)}")
    
    def _edit_tag(self):
        """编辑标签"""
        try:
            # 获取选中的标签
            items = self.tag_list.selectedItems()
            if not items:
                QMessageBox.warning(self, "警告", "请选择要编辑的标签")
                return
            
            row = items[0].row()
            old_name = self.tag_list.item(row, 0).text()
            old_category = self.tag_list.item(row, 1).text()
            if old_category == "未分类":
                old_category = None
            
            # 显示编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑标签")
            layout = QVBoxLayout(dialog)
            
            # 标签名称输入
            name_layout = QHBoxLayout()
            name_label = QLabel("标签名称:")
            name_edit = QLineEdit(old_name)
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_edit)
            
            # 分类选择
            category_layout = QHBoxLayout()
            category_label = QLabel("分类:")
            category_combo = QComboBox()
            category_combo.addItem("未分类")
            categories = self.image_processor.get_tag_categories()
            for cat in categories:
                category_combo.addItem(cat)
            if old_category:
                index = category_combo.findText(old_category)
                if index >= 0:
                    category_combo.setCurrentIndex(index)
            category_layout.addWidget(category_label)
            category_layout.addWidget(category_combo)
            
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
            layout.addLayout(category_layout)
            layout.addLayout(btn_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_name = name_edit.text().strip()
                new_category = category_combo.currentText()
                if new_category == "未分类":
                    new_category = None
                
                # 更新标签
                tag_id = self.image_processor.get_tag_id(old_name)
                if tag_id:
                    self.image_processor.update_tag(tag_id, new_name, new_category)
                    # 刷新列表
                    self._load_data()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑标签失败：{str(e)}")
    
    def _remove_tag(self):
        """删除标签"""
        try:
            # 获取选中的标签
            items = self.tag_list.selectedItems()
            if not items:
                QMessageBox.warning(self, "警告", "请选择要删除的标签")
                return
            
            row = items[0].row()
            tag_name = self.tag_list.item(row, 0).text()
            usage_count = int(self.tag_list.item(row, 2).text())
            
            # 确认删除
            message = f"确定要删除标签 '{tag_name}' 吗？"
            if usage_count > 0:
                message += f"\n该标签已被使用 {usage_count} 次"
            
            reply = QMessageBox.question(
                self, "确认删除", message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 获取标签ID并删除
                tag_id = self.image_processor.get_tag_id(tag_name)
                if tag_id:
                    self.image_processor.delete_tag(tag_id)
                    # 刷新列表
                    self._load_data()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除标签失败：{str(e)}") 