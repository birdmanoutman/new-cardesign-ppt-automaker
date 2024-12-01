from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, 
    QProgressBar, QCheckBox, QGroupBox, QGridLayout, QHeaderView,
    QApplication
)
from PyQt6.QtCore import Qt
from functools import partial
import os
import shutil
from datetime import datetime
from .base_tab import BaseTab

class FileTab(BaseTab):
    def __init__(self, file_manager, parent=None):
        self.file_manager = file_manager
        super().__init__(parent)
    
    def init_ui(self):
        """初始化文件名标准化标签页的UI"""
        # 文件夹选择区域
        folder_group = QGroupBox("文件夹选择")
        folder_layout = QGridLayout()
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择文件夹")
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse_folder)
        
        folder_layout.addWidget(QLabel("文件夹:"), 0, 0)
        folder_layout.addWidget(self.path_input, 0, 1)
        folder_layout.addWidget(browse_btn, 0, 2)
        
        folder_group.setLayout(folder_layout)
        self.layout.addWidget(folder_group)
        
        # 规则设置区域
        rules_group = QGroupBox("命名规则")
        rules_layout = QGridLayout()
        
        self.add_date_checkbox = QCheckBox("添加默认日期")
        self.add_date_checkbox.setChecked(True)
        self.add_date_checkbox.stateChanged.connect(self._on_rule_changed)
        
        self.rename_folders_checkbox = QCheckBox("重命名文件夹")
        self.rename_folders_checkbox.stateChanged.connect(self._on_rule_changed)
        
        self.camel_case_checkbox = QCheckBox("驼峰命名")
        self.camel_case_checkbox.stateChanged.connect(self._on_rule_changed)
        
        rules_layout.addWidget(self.add_date_checkbox, 0, 0)
        rules_layout.addWidget(self.rename_folders_checkbox, 0, 1)
        rules_layout.addWidget(self.camel_case_checkbox, 0, 2)
        
        rules_group.setLayout(rules_layout)
        self.layout.addWidget(rules_group)
        
        # 参考日期全选控制
        ref_date_control_layout = QHBoxLayout()
        self.ref_date_all_checkbox = QCheckBox("全选参考内容日期")
        self.ref_date_all_checkbox.setTristate(True)
        self.ref_date_all_checkbox.clicked.connect(self._on_ref_date_all_clicked)
        ref_date_control_layout.addWidget(self.ref_date_all_checkbox)
        ref_date_control_layout.addStretch()
        
        self.layout.addLayout(ref_date_control_layout)
        
        # 文件预览区域
        preview_group = QGroupBox("文件预览")
        preview_layout = QVBoxLayout()
        
        # 添加全选控制 - 在使用前先定义
        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.setTristate(True)  # 启用三态
        self.select_all_checkbox.clicked.connect(self._on_select_all_clicked)
        
        # 创建顶部工具栏布局
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.select_all_checkbox)
        toolbar_layout.addStretch()  # 添加弹性空间
        toolbar_layout.addWidget(self.ref_date_all_checkbox)  # 将复选框添加到最右侧
        
        preview_layout.addLayout(toolbar_layout)
        
        # 创建文件列表表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels([
            "选择", "类型", "原文件名", "标准化文件名", "参考文件夹中内容日期"
        ])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        preview_layout.addWidget(self.file_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("应用更改")
        apply_btn.clicked.connect(self._apply_changes)
        undo_btn = QPushButton("撤销更改")
        undo_btn.clicked.connect(self._undo_changes)
        
        button_layout.addWidget(undo_btn)
        button_layout.addWidget(apply_btn)
        button_layout.addStretch()
        
        preview_layout.addLayout(button_layout)
        preview_group.setLayout(preview_layout)
        self.layout.addWidget(preview_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

    def _browse_folder(self):
        """浏览文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.path_input.setText(folder_path)
            self._preview_changes()

    def _on_rule_changed(self):
        """规则设置改变时更新预览"""
        if self.path_input.text():
            # 重新生成所有文件名预览
            self._preview_changes()
            
            # 更新全选复选框状态
            self._update_select_all_state()

    def _on_ref_date_all_clicked(self):
        """处理参考日期全选复选框点击事件"""
        is_checked = self.ref_date_all_checkbox.isChecked()
        self.ref_date_all_checkbox.setTristate(False)
        
        # 更新所有文件夹的参考日期选择状态
        for row in range(self.file_table.rowCount()):
            ref_date_checkbox = self.file_table.cellWidget(row, 4)
            if isinstance(ref_date_checkbox, QCheckBox):
                ref_date_checkbox.setChecked(is_checked)
                
                # 获取原始文件名和新文件名
                original_name = self.file_table.item(row, 2).text()
                new_name = self.file_table.item(row, 3).text()
                
                # 只有当新文件名与原文件名不同时，才勾选选择框
                checkbox = self.file_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(new_name != original_name)

    def _preview_changes(self):
        """预览文件重命名结果"""
        folder_path = self.path_input.text()
        if not folder_path:
            return
        
        # 获取规则设置
        rules = {
            'add_default_date': self.add_date_checkbox.isChecked(),
            'rename_folders': self.rename_folders_checkbox.isChecked(),
            'use_camel_case': self.camel_case_checkbox.isChecked()
        }
        
        # 暂时阻止表格更新
        self.file_table.setUpdatesEnabled(False)
        
        try:
            # 断开信号前先检查是否已连接
            try:
                self.file_table.itemChanged.disconnect(self._on_table_item_changed)
            except TypeError:
                pass
            
            # 清空表格
            self.file_table.setRowCount(0)
            
            # 获取文件列表
            files = os.listdir(folder_path)
            regular_files = []
            folders = []
            
            # 过滤和分类文件
            for filename in files:
                if self.file_manager.should_ignore_file(filename):
                    continue
                    
                filepath = os.path.join(folder_path, filename)
                is_folder = os.path.isdir(filepath)
                
                if is_folder:
                    # 只有当启用文件夹重命名且不在排除列表中时才添加
                    if rules['rename_folders'] and not self.file_manager.should_ignore_folder_rename(filename):
                        folders.append(filename)
                else:
                    regular_files.append(filename)
            
            # 加文件夹
            for filename in folders:
                self._add_file_to_table(filename, folder_path, True, rules)
            
            # 添加普通文件
            for filename in regular_files:
                self._add_file_to_table(filename, folder_path, False, rules)
                
        finally:
            # 恢复表格更新和信号连接
            self.file_table.setUpdatesEnabled(True)
            self.file_table.itemChanged.connect(self._on_table_item_changed)

    def _add_file_to_table(self, filename: str, folder_path: str, is_folder: bool, rules: dict):
        """添加文件到预览表格"""
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        
        # 添加选择框
        checkbox = QCheckBox()
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(self._update_select_all_state)  # 添加状态变化处理
        self.file_table.setCellWidget(row, 0, checkbox)
        
        # 设置类型
        type_item = QTableWidgetItem("文件夹" if is_folder else "文件")
        type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.file_table.setItem(row, 1, type_item)
        
        # 设置原文件名
        original_item = QTableWidgetItem(filename)
        original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.file_table.setItem(row, 2, original_item)
        
        # 设置标准化文件名
        filepath = os.path.join(folder_path, filename)
        new_name = self.file_manager.standardize_filename(filepath, rules)
        new_name_item = QTableWidgetItem(new_name)
        self.file_table.setItem(row, 3, new_name_item)
        
        # 如果新文件名与原文件名不同，自动勾选
        if new_name != filename:
            checkbox.setChecked(True)
        
        # 设置参考日期选项
        if is_folder and rules['rename_folders']:
            ref_date_checkbox = QCheckBox()
            ref_date_checkbox.setChecked(False)
            ref_date_checkbox.stateChanged.connect(
                lambda state, row=row, folder_path=filepath: 
                self._on_ref_date_changed(state, row, folder_path)
            )
            self.file_table.setCellWidget(row, 4, ref_date_checkbox)
        else:
            # 非文件夹或未启用文件夹重命名时，该列为空
            self.file_table.setItem(row, 4, QTableWidgetItem(""))

    def _on_table_item_changed(self, item):
        """处理表格项变化事件"""
        if item.column() == 3:  # 标准化文件名列
            try:
                # 暂时断开信号连接，避免递归
                self.file_table.itemChanged.disconnect(self._on_table_item_changed)
                
                # 获取原始文件名
                original_name = self.file_table.item(item.row(), 2).text()
                new_name = item.text()
                
                # 如果文件名没有变化，不需要处理
                if new_name == original_name:
                    return
                
                # 检查新文件名是否有效
                if not new_name or '/' in new_name or '\\' in new_name:
                    item.setText(original_name)
                    QMessageBox.warning(self, "警告", "文件名不能为空或包含路径分隔符")
                    return
                
                # 检查新文件名是否已存在
                folder_path = self.path_input.text()
                if os.path.exists(os.path.join(folder_path, new_name)):
                    item.setText(original_name)
                    QMessageBox.warning(self, "警告", "文件名已存在")
                    return
                
                # 更新选择框状态
                checkbox = self.file_table.cellWidget(item.row(), 0)
                if checkbox:
                    checkbox.setChecked(True)
                    
            finally:
                # 恢复信号连接
                self.file_table.itemChanged.connect(self._on_table_item_changed)

    def _get_folder_earliest_date(self, folder_path: str) -> tuple[datetime | None, bool]:
        """
        获取文件夹中演示文件的最早日期
        返回值: (最早日期, 是否存在演示文件)
        """
        earliest_date = None
        has_ppt_files = False
        
        try:
            # 确保文件夹路径存在
            if not os.path.exists(folder_path):
                return None, False
            
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.pptx', '.ppt', '.key', '.keynote')):
                        has_ppt_files = True
                        file_path = os.path.join(root, file)
                        try:
                            ctime = datetime.fromtimestamp(os.path.getctime(file_path))
                            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            file_date = min(ctime, mtime)
                            
                            if earliest_date is None or file_date < earliest_date:
                                earliest_date = file_date
                        except Exception as e:
                            print(f"获取文件 {file} 日期时出错: {str(e)}")
                            continue
        except Exception as e:
            print(f"遍历文件夹 {folder_path} 时出错: {str(e)}")
        
        return earliest_date, has_ppt_files

    def _on_ref_date_changed(self, state: int, row: int, folder_path: str):
        """处理文件夹内容日期参考选项变化"""
        try:
            # 获取原始文件名和当前规则
            original_name = self.file_table.item(row, 2).text()
            rules = {
                'add_default_date': True,  # 强制添加日期
                'rename_folders': self.rename_folders_checkbox.isChecked(),
                'use_camel_case': self.camel_case_checkbox.isChecked()
            }
            
            if state == Qt.CheckState.Checked.value:
                # 获取文件夹中最早的演示文件日期
                full_path = os.path.join(self.path_input.text(), original_name)
                earliest_date, has_ppt_files = self._get_folder_earliest_date(full_path)
                
                if not has_ppt_files:
                    # 如果没有演示文件，静默取消勾选并返回
                    ref_date_checkbox = self.file_table.cellWidget(row, 4)
                    if ref_date_checkbox:
                        ref_date_checkbox.blockSignals(True)
                        ref_date_checkbox.setChecked(False)
                        ref_date_checkbox.blockSignals(False)
                    return
                
                if earliest_date:
                    # 从原始文件名中提取非日期部分
                    _, name_without_date = self.file_manager._extract_and_remove_date(
                        original_name, 
                        datetime.now(),
                        True
                    )
                    
                    # 如果启用了驼峰命名，先处理非日期部分
                    if rules['use_camel_case']:
                        name_without_date = self.file_manager._to_camel_case(name_without_date)
                    
                    # 生成新文件名（确保日期和名称之间有下划线）
                    date_str = earliest_date.strftime('%Y%m%d')
                    new_name = f"{date_str}_{name_without_date}"
                    
                    # 更新表格中的新文件名
                    new_name_item = self.file_table.item(row, 3)
                    if new_name_item:
                        new_name_item.setText(new_name)
                        
                    # 更新选择框状态
                    checkbox = self.file_table.cellWidget(row, 0)
                    if checkbox:
                        checkbox.setChecked(new_name != original_name)
            else:
                # 取消选中时，使用原始文件名重新生成标准化名称
                rules['add_default_date'] = self.add_date_checkbox.isChecked()
                new_name = self.file_manager.standardize_filename(
                    original_name,  # 使用原始文件名
                    rules
                )
                
                # 更新表格中的新文件名
                new_name_item = self.file_table.item(row, 3)
                if new_name_item:
                    new_name_item.setText(new_name)
            
            # 更新全选复选框状态
            self._update_ref_date_all_state()
            
        except Exception as e:
            print(f"处理参考日期变化时出错: {str(e)}")
            # 发生错误时，恢复复选框状态
            ref_date_checkbox = self.file_table.cellWidget(row, 4)
            if ref_date_checkbox:
                ref_date_checkbox.blockSignals(True)
                ref_date_checkbox.setChecked(False)
                ref_date_checkbox.blockSignals(False)

    def _update_ref_date_all_state(self):
        """更新参考日期全选复选框状态"""
        total_folders = 0
        checked_folders = 0
        
        for row in range(self.file_table.rowCount()):
            ref_date_checkbox = self.file_table.cellWidget(row, 4)
            if isinstance(ref_date_checkbox, QCheckBox):
                total_folders += 1
                if ref_date_checkbox.isChecked():
                    checked_folders += 1
        
        self.ref_date_all_checkbox.blockSignals(True)
        
        if total_folders == 0:
            self.ref_date_all_checkbox.setChecked(False)
        elif checked_folders == 0:
            self.ref_date_all_checkbox.setChecked(False)
        elif checked_folders == total_folders:
            self.ref_date_all_checkbox.setChecked(True)
        else:
            self.ref_date_all_checkbox.setTristate(True)
            self.ref_date_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        
        self.ref_date_all_checkbox.blockSignals(False)

    def _apply_changes(self):
        """应用文件重命名更改"""
        folder_path = self.path_input.text()
        if not folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹")
            return
        
        # 收集需要重命名的文件
        rename_tasks = []
        for row in range(self.file_table.rowCount()):
            checkbox = self.file_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                original_name = self.file_table.item(row, 2).text()
                new_name = self.file_table.item(row, 3).text()
                if new_name != original_name:
                    rename_tasks.append((original_name, new_name))
        
        if not rename_tasks:
            QMessageBox.information(self, "提示", "没有需要重命名的文件")
            return
        
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            "确认重命名",
            f"确定要重命名 {len(rename_tasks)} 个文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 显示进度条
                self.progress_bar.setVisible(True)
                self.progress_bar.setMaximum(len(rename_tasks))
                self.progress_bar.setValue(0)
                
                # 执行重命名
                success_count = 0
                error_count = 0
                error_messages = []
                
                for i, (original_name, new_name) in enumerate(rename_tasks):
                    try:
                        original_path = os.path.join(folder_path, original_name)
                        new_path = os.path.join(folder_path, new_name)
                        
                        # 检查目标文件是否已存在
                        if os.path.exists(new_path):
                            error_count += 1
                            error_messages.append(f"无法重命名 {original_name}：目标文件已存在")
                            continue
                        
                        # 执行重命名
                        if os.path.isdir(original_path):
                            os.rename(original_path, new_path)
                        else:
                            shutil.move(original_path, new_path)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"重命名 {original_name} 时出错：{str(e)}")
                    
                    # 更新进度条
                    self.progress_bar.setValue(i + 1)
                    QApplication.processEvents()
                
                # 显示完成消息
                message = f"重命名完成\n成功: {success_count}\n失败: {error_count}"
                if error_messages:
                    message += "\n\n错误详情:\n" + "\n".join(error_messages[:5])
                    if len(error_messages) > 5:
                        message += f"\n... 等共 {len(error_messages)} 个错误"
                
                if error_count > 0:
                    QMessageBox.warning(self, "完成(有错误)", message)
                else:
                    QMessageBox.information(self, "完��", message)
                
                # 刷新预览
                self._preview_changes()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名时出错：{str(e)}")
            finally:
                self.progress_bar.setVisible(False)

    def _undo_changes(self):
        """撤销文件重命名操作"""
        folder_path = self.path_input.text()
        if not folder_path:
            return
        
        try:
            # 获取表格中的重命名记录
            rename_records = []
            for row in range(self.file_table.rowCount()):
                new_name = self.file_table.item(row, 3).text()
                original_name = self.file_table.item(row, 2).text()
                if new_name != original_name:
                    rename_records.append((new_name, original_name))
            
            if not rename_records:
                QMessageBox.information(self, "提示", "没有需撤销的更改")
                return
            
            # 确认是否撤销
            reply = QMessageBox.question(
                self, 
                "确认撤销", 
                f"确定要撤销所有重命名操作吗？\n这将恢复 {len(rename_records)} 个文件的原始名称。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 设置进度条
                self.progress_bar.setVisible(True)
                self.progress_bar.setMaximum(len(rename_records))
                self.progress_bar.setValue(0)
                
                # 执行撤销操作
                success_count = 0
                error_count = 0
                error_messages = []
                
                for i, (current_name, original_name) in enumerate(rename_records):
                    try:
                        current_path = os.path.join(folder_path, current_name)
                        original_path = os.path.join(folder_path, original_name)
                        
                        # 检查目标路径是否已存在
                        if os.path.exists(original_path):
                            error_count += 1
                            error_messages.append(f"无法恢复 {current_name}：目标文件名已存在")
                            continue
                        
                        # 执行重命名
                        if os.path.exists(current_path):
                            if os.path.isdir(current_path):
                                os.rename(current_path, original_path)
                            else:
                                shutil.move(current_path, original_path)
                            success_count += 1
                        else:
                            error_count += 1
                            error_messages.append(f"找不到文件：{current_name}")
                            
                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"重命名 {current_name} 时出错：{str(e)}")
                    
                    # 更新进度条
                    self.progress_bar.setValue(i + 1)
                    QApplication.processEvents()
                
                # 显示完成消息
                message = f"撤销完成\n成功: {success_count}\n失败: {error_count}"
                if error_messages:
                    message += "\n\n错误详情:\n" + "\n".join(error_messages[:5])
                    if len(error_messages) > 5:
                        message += f"\n... 等共 {len(error_messages)} 个错误"
                
                if error_count > 0:
                    QMessageBox.warning(self, "完成(有错误)", message)
                else:
                    QMessageBox.information(self, "完成", message)
                
                # 刷新预览
                self._preview_changes()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"撤销更改时出错：{str(e)}")
        finally:
            self.progress_bar.setVisible(False)

    def _on_select_all_clicked(self):
        """处理全选复选框点击事件"""
        is_checked = self.select_all_checkbox.isChecked()
        self.select_all_checkbox.setTristate(False)  # 禁用三态，避免循环
        
        # 更新所有文件的选择状态
        for row in range(self.file_table.rowCount()):
            checkbox = self.file_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(is_checked)
        
        # 恢复三态
        self.select_all_checkbox.setTristate(True)

    def _update_select_all_state(self):
        """更新全选复选框状态"""
        total_files = 0
        checked_files = 0
        
        for row in range(self.file_table.rowCount()):
            checkbox = self.file_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                total_files += 1
                if checkbox.isChecked():
                    checked_files += 1
        
        self.select_all_checkbox.blockSignals(True)
        
        if total_files == 0:
            self.select_all_checkbox.setChecked(False)
        elif checked_files == 0:
            self.select_all_checkbox.setChecked(False)
        elif checked_files == total_files:
            self.select_all_checkbox.setChecked(True)
        else:
            self.select_all_checkbox.setTristate(True)
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        
        self.select_all_checkbox.blockSignals(False)