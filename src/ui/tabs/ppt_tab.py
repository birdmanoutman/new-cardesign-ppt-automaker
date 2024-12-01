from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QGridLayout,
    QTextEdit
)
from PyQt6.QtCore import Qt, QSize, QTimer
import os
from pathlib import Path
from .base_tab import BaseTab
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

class PPTTab(BaseTab):
    def __init__(self, ppt_processor, parent=None):
        self.ppt_processor = ppt_processor
        super().__init__(parent)
        self.setAcceptDrops(True)
    
    def init_ui(self):
        """初始化PPT快捷操作标签页的UI"""
        # PPT文件选择区域
        ppt_group = QGroupBox("PPT文件")
        ppt_layout = QGridLayout()
        
        self.ppt_path_input = QLineEdit()
        self.ppt_path_input.setPlaceholderText("选择PPT文件")
        self.ppt_path_input.setMinimumWidth(300)
        
        ppt_browse_btn = QPushButton("浏览")
        ppt_browse_btn.clicked.connect(self._browse_ppt)
        
        ppt_layout.addWidget(QLabel("PPT文件:"), 0, 0)
        ppt_layout.addWidget(self.ppt_path_input, 0, 1)
        ppt_layout.addWidget(ppt_browse_btn, 0, 2)
        
        ppt_group.setLayout(ppt_layout)
        self.layout.addWidget(ppt_group)
        
        # 快捷操作区域
        quick_actions_group = QGroupBox("快捷操作")
        quick_actions_layout = QVBoxLayout()
        
        # 提取图片区域
        image_group = QGroupBox("图片提取")
        image_layout = QVBoxLayout()
        
        # 添加输出文件夹选择
        output_folder_layout = QHBoxLayout()
        self.output_folder_input = QLineEdit()
        self.output_folder_input.setPlaceholderText("选择图片保存位置")
        self.output_folder_input.setMinimumWidth(300)
        
        output_folder_btn = QPushButton("浏览")
        output_folder_btn.clicked.connect(self._browse_output_folder)
        
        output_folder_layout.addWidget(QLabel("保存位置:"))
        output_folder_layout.addWidget(self.output_folder_input)
        output_folder_layout.addWidget(output_folder_btn)
        
        # 提取按钮
        extract_images_btn = QPushButton("提取所有图片")
        extract_images_btn.clicked.connect(self._extract_ppt_images)
        
        image_layout.addLayout(output_folder_layout)
        image_layout.addWidget(extract_images_btn)
        image_group.setLayout(image_layout)
        quick_actions_layout.addWidget(image_group)
        
        # 添加文字提取区域
        text_group = QGroupBox("文字提取")
        text_layout = QVBoxLayout()
        
        # 添加提取按钮和说明
        button_layout = QHBoxLayout()
        extract_text_btn = QPushButton("提取所有文字")
        extract_text_btn.clicked.connect(self._extract_ppt_text)
        button_layout.addWidget(extract_text_btn)
        button_layout.addStretch()  # 添加弹性空间
        text_layout.addLayout(button_layout)
        
        # 添加文本显示区域
        self.text_display = QTextEdit()
        # self.text_display.setReadOnly(True)  # 移除只读属性
        self.text_display.setPlaceholderText("提取的文字将显示在这里...\n您可以直接编辑文本内容")
        self.text_display.setMinimumHeight(200)
        text_layout.addWidget(self.text_display)
        
        # 添加复制按钮
        copy_text_btn = QPushButton("复制全部文字")  # 更明确的按钮文字
        copy_text_btn.clicked.connect(self._copy_extracted_text)
        text_layout.addWidget(copy_text_btn)
        
        text_group.setLayout(text_layout)
        quick_actions_layout.addWidget(text_group)
        
        # 其他快捷操作按钮
        clean_master_btn = QPushButton("清理母版")
        clean_master_btn.clicked.connect(self._clean_ppt_layouts)
        
        adjust_text_btn = QPushButton("调整文本框")
        adjust_text_btn.clicked.connect(self._adjust_ppt_textboxes)
        
        quick_actions_layout.addWidget(clean_master_btn)
        quick_actions_layout.addWidget(adjust_text_btn)
        
        quick_actions_group.setLayout(quick_actions_layout)
        self.layout.addWidget(quick_actions_group)
        
        # 进度条
        self.ppt_progress_bar = QProgressBar()
        self.ppt_progress_bar.setVisible(False)
        self.layout.addWidget(self.ppt_progress_bar)
        
        # 添加弹性空间
        self.layout.addStretch()
        
        # 如果之前有选择过PPT文件，恢复路径
        last_ppt_path = QSettings().value("last_ppt_path", "")
        if last_ppt_path and os.path.exists(last_ppt_path):
            self.ppt_path_input.setText(last_ppt_path)
            # 设置默认输出文件夹
            default_output = os.path.join(os.path.dirname(last_ppt_path), 'images')
            self.output_folder_input.setText(default_output)

    def _browse_ppt(self):
        """选择PPT文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PPT文件", "", "PowerPoint Files (*.pptx *.ppt)"
        )
        if file_path:
            self.ppt_path_input.setText(file_path)
            # 保存路径
            QSettings().setValue("last_ppt_path", file_path)
            
            # 如果没有设置输出文件夹，默认使用PPT所在文件夹下的images子文件夹
            if not self.output_folder_input.text():
                default_output = os.path.join(os.path.dirname(file_path), 'images')
                self.output_folder_input.setText(default_output)

    def _browse_output_folder(self):
        """选择图片输出文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片保存位置")
        if folder_path:
            self.output_folder_input.setText(folder_path)

    def _check_ppt_file(self) -> bool:
        """检查是否选择了PPT文件"""
        if not self.ppt_path_input.text():
            # 直接打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择PPT文件", "", "PowerPoint Files (*.pptx *.ppt)"
            )
            if file_path:
                self.ppt_path_input.setText(file_path)
                return True
            return False
        return True

    def _extract_ppt_images(self):
        """从PPT中提取所有图片"""
        if not self._check_ppt_file():
            return
        
        output_folder = self.output_folder_input.text()
        if not output_folder:
            # 使用PPT所在文件夹下的images子文件夹
            ppt_folder = os.path.dirname(self.ppt_path_input.text())
            output_folder = os.path.join(ppt_folder, 'images')
            self.output_folder_input.setText(output_folder)
            
            # 确保输出文件夹存在
            os.makedirs(output_folder, exist_ok=True)
        
        try:
            # 显示进度条
            self.ppt_progress_bar.setVisible(True)
            self.ppt_progress_bar.setMaximum(0)  # 显示忙碌状态
            
            # 打开PPT文件
            self.ppt_processor.open_presentation(self.ppt_path_input.text())
            
            # 提取图片
            extracted_images = self.ppt_processor.extract_all_images(output_folder)
            
            # 显示结果
            if extracted_images:
                QMessageBox.information(
                    self,
                    "完成",
                    f"成功提取 {len(extracted_images)} 张图片\n保存位置：{output_folder}"
                )
                
                # 打开输出文件夹
                if os.name == 'nt':  # Windows
                    os.system(f'explorer "{output_folder}"')
                else:  # macOS 和 Linux
                    os.system(f'open "{output_folder}"')
            else:
                QMessageBox.information(self, "完成", "未找到图片")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提取图片时出错：{str(e)}")
        finally:
            self.ppt_progress_bar.setVisible(False)

    def _clean_ppt_layouts(self):
        """清理PPT母版"""
        if not self._check_ppt_file():
            return
        
        try:
            # 显示进度条
            self.ppt_progress_bar.setVisible(True)
            self.ppt_progress_bar.setMaximum(0)  # 显示忙碌状态
            
            # 打开PPT文件
            self.ppt_processor.open_presentation(self.ppt_path_input.text())
            
            # 清理母版
            cleaned_count = self.ppt_processor.clean_unused_layouts()
            
            # 显示结果
            QMessageBox.information(
                self,
                "完成",
                f"清理完成，共移除{cleaned_count}个未使用的布局"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"清理模板时出错：{str(e)}")
        finally:
            self.ppt_progress_bar.setVisible(False)

    def _adjust_ppt_textboxes(self):
        """调整PPT文本框"""
        if not self._check_ppt_file():
            return
        
        try:
            # 显示进度条
            self.ppt_progress_bar.setVisible(True)
            self.ppt_progress_bar.setMaximum(0)  # 显示忙碌状态
            
            # 打开PPT文件
            self.ppt_processor.open_presentation(self.ppt_path_input.text())
            
            # 调整文本框
            self.ppt_processor.adjust_text_boxes()
            
            # 显示结果
            QMessageBox.information(self, "完成", "文本框调整完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"调整文本框时出错：{str(e)}")
        finally:
            self.ppt_progress_bar.setVisible(False)

    def _extract_ppt_text(self):
        """提取PPT中的所有文字"""
        if not self._check_ppt_file():
            return
        
        try:
            # 显示进度条
            self.ppt_progress_bar.setVisible(True)
            self.ppt_progress_bar.setMaximum(0)  # 显示忙碌状态
            
            # 打开PPT文件
            self.ppt_processor.open_presentation(self.ppt_path_input.text())
            
            # 提取文字
            extracted_text = self.ppt_processor.extract_text()
            
            # 显示提取的文字
            self.text_display.setText(extracted_text)
            
            # 显示结果
            QMessageBox.information(self, "完成", "文字提取完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提取文字时出错：{str(e)}")
        finally:
            self.ppt_progress_bar.setVisible(False)
    
    def _copy_extracted_text(self):
        """复制提取的文字到剪贴板"""
        if self.text_display.toPlainText():
            # 获取文本并复制到剪贴板
            self.text_display.selectAll()
            self.text_display.copy()
            self.text_display.moveCursor(self.text_display.textCursor().Start)  # 移动光标到开始位置
            
            # 显示提示
            QMessageBox.information(self, "提示", "文字已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "没有可复制的文字")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.ppt', '.pptx')):
                    event.acceptProposedAction()
                    return
    
    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.ppt', '.pptx')):
                self.ppt_path_input.setText(file_path)
                # 设置默认输出文件夹
                default_output = os.path.join(os.path.dirname(file_path), 'images')
                self.output_folder_input.setText(default_output)
                break

    # ... (继续实现其他方法)