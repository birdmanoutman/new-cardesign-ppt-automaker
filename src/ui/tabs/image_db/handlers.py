from PyQt6.QtWidgets import (
    QMessageBox, QFileDialog, QProgressDialog, QMenu,
    QTableWidgetItem, QDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage
from pathlib import Path
import os
import io
from PIL import Image
import win32clipboard
import win32con

# 修改相对导入路径
from ...dialogs.tag_manager_dialog import TagManagerDialog
from .image_item import ImageItem

class ImageDBHandlers:
    """事件处理器"""
    def __init__(self, tab, ui, ppt_processor):
        self.tab = tab
        self.ui = ui
        self.ppt_processor = ppt_processor
        self.current_page = 0
        self.page_size = 1000
        self.is_loading = False
        self.has_more = True
        self.all_images = []
        self.loaded_images = set()
        self.cleanup_handlers = []  # 添加清理处理器列表
        
        # 连接信号
        self._connect_signals()

    def _connect_signals(self):
        """连接信号到处理函数"""
        components = self.ui.get_components()
        
        # 搜索和过滤
        components['image_search'].textChanged.connect(self._filter_images)
        components['tag_filter'].currentTextChanged.connect(self._filter_images)
        components['match_all_tags'].stateChanged.connect(self._filter_images)
        
        # 图片网格
        components['image_grid'].customContextMenuRequested.connect(self._show_image_context_menu)
        components['image_grid'].verticalScrollBar().valueChanged.connect(self._check_scroll_position)

    def load_database_state(self):
        """加载数据库状态"""
        try:
            image_processor = self.ppt_processor.get_image_processor()
            components = self.ui.get_components()
            
            # 加载已有的PPT源文件夹
            for source_path in image_processor.get_ppt_sources():
                if Path(source_path).exists():
                    row = components['source_table'].rowCount()
                    components['source_table'].insertRow(row)
                    components['source_table'].setItem(row, 0, QTableWidgetItem(source_path))
                    components['source_table'].setItem(row, 1, QTableWidgetItem("已添加"))
            
            # 加载图片库路径
            lib_path = image_processor.get_setting('image_lib_path')
            if lib_path:
                components['image_lib_path'].setText(lib_path)
            
            # 更新标签过滤器
            self._update_tag_filter()
            
            # 显示图片
            self._display_database_images()
            
            # 更新数据库状态
            stats = image_processor.get_image_stats()
            if stats:
                components['db_status_label'].setText(
                    f"数据库状态: {stats['total']} 张图片，来自 {stats['ppt_count']} 个PPT"
                )
            
        except Exception as e:
            print(f"加载数据库状态时出错: {str(e)}")

    def _filter_images(self):
        """根据搜索文本和标签过滤图片"""
        try:
            components = self.ui.get_components()
            search_text = components['image_search'].text().lower()
            selected_tag = components['tag_filter'].currentText().strip()
            match_all = components['match_all_tags'].isChecked()
            
            # 获取图片处理器
            image_processor = self.ppt_processor.get_image_processor()
            
            # 初始化搜索标签集合
            search_tags = set()
            
            # 添加下拉框选中的标签
            if selected_tag != "所有标签" and not (selected_tag.startswith('─') or selected_tag.startswith('【')):
                search_tags.add(selected_tag)
            
            # 从搜索文本中提取标签
            if search_text:
                # 获取所有标签
                all_tags = {tag['name'].lower(): tag['name'] 
                          for tag in image_processor.get_all_tags()}
                
                # 提取带引号的标签
                import re
                quoted_terms = re.findall(r'"([^"]+)"', search_text)
                
                # 处理带引号的标签
                for term in quoted_terms:
                    term = term.lower()
                    if term in all_tags:
                        search_tags.add(all_tags[term])
                        # 从搜索文本中移除已处理的标签
                        search_text = search_text.replace(f'"{term}"', '')
                
                # 处理剩余的单个词
                remaining_terms = [t for t in search_text.split() if t]
                for term in remaining_terms:
                    if term in all_tags:
                        search_tags.add(all_tags[term])
                        # 从搜索文本中移除已处理的标签
                        search_text = search_text.replace(term, '')
            
            # 获取图片列表
            if search_tags:
                # 有标签过滤
                print(f"搜索标签: {search_tags} ({'AND' if match_all else 'OR'})")
                images = image_processor.search_images_by_tags(
                    tuple(sorted(search_tags)),
                    match_all=match_all  # 使用匹配所有标签的设置
                )
                
                # 处理剩余的搜索文本（非标签部分）
                search_text = search_text.strip()
                if search_text:
                    images = [img for img in images 
                             if search_text in img['name'].lower()]
            else:
                # 无标签过滤，获取所有图片
                images = image_processor.get_all_images()
                # 如果有搜索文本，按名称过滤
                if search_text:
                    images = [img for img in images 
                             if search_text in img['name'].lower()]
            
            # 重置分页状态
            self.current_page = 0
            self.has_more = True
            
            # 显示结果
            self._display_database_images(images)
            
            # 更新状态
            status_text = f"显示 {len(images)} 张图片"
            if search_tags:
                status_text += f" (标签: {', '.join(search_tags)})"
                if len(search_tags) > 1:
                    status_text += f" ({('全部匹配' if match_all else '任意匹配')})"
            components['db_status_label'].setText(status_text)
            
        except Exception as e:
            print(f"过滤图片失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def _display_database_images(self, images=None):
        """显示数据库中的图片"""
        try:
            components = self.ui.get_components()
            
            # 清空当前显示
            components['image_grid'].clear()
            self.loaded_images.clear()
            
            if images is None:
                # 如果没有指定图片列表，获取所有图片
                image_processor = self.ppt_processor.get_image_processor()
                images = image_processor.get_all_images()
            
            # 保存完整的图片列表
            self.all_images = images
            self.total_images = len(images)
            
            # 只显示第一页的图片
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
            components = self.ui.get_components()
            
            # 计算当前页的图片范围
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, self.total_images)
            current_images = self.all_images[start_idx:end_idx]
            
            if not current_images:
                print(f"没有更多图片可加载 ({start_idx}-{end_idx}/{self.total_images})")
                return
            
            print(f"加载图片 {start_idx}-{end_idx}/{self.total_images}")
            
            # 批量加载缩略图
            image_processor = self.ppt_processor.get_image_processor()
            thumb_paths = image_processor.batch_create_thumbnails(
                [img['path'] for img in current_images],
                [img.get('ref_count', 0) for img in current_images]
            )
            
            # 批量创建图片项
            for img_info, thumb_path in zip(current_images, thumb_paths):
                if img_info['hash'] not in self.loaded_images:
                    try:
                        item = ImageItem.create_item(img_info, thumb_path, image_processor)
                        if item:
                            components['image_grid'].addItem(item)
                            self.loaded_images.add(img_info['hash'])
                    except Exception as e:
                        print(f"加载图片失败: {str(e)}")
            
            # 更新状态
            components['db_status_label'].setText(
                f"显示 {len(self.loaded_images)}/{self.total_images} 张图片"
            )
            
            # 检查是否还有更多图片
            self.has_more = end_idx < self.total_images
            
        except Exception as e:
            print(f"加载页面失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def _check_scroll_position(self):
        """检查滚动位置，决定是否加载下一页"""
        if self.is_loading or not self.has_more:
            return
        
        components = self.ui.get_components()
        scrollbar = components['image_grid'].verticalScrollBar()
        
        # 当滚动到底部80%时加载更多
        threshold = scrollbar.maximum() * 0.8
        if scrollbar.value() >= threshold:
            print(f"触发加载更多: {scrollbar.value()}/{scrollbar.maximum()}")
            self._load_more_images()

    def _load_more_images(self):
        """加载更多图片"""
        if self.is_loading or not self.has_more:
            return
            
        self.is_loading = True
        try:
            self.current_page += 1
            self._load_page()
            self.has_more = (self.current_page + 1) * self.page_size < self.total_images
        finally:
            self.is_loading = False

    def _update_tag_filter(self):
        """更新标签过滤下拉框"""
        try:
            components = self.ui.get_components()
            image_processor = self.ppt_processor.get_image_processor()
            tags = image_processor.get_all_tags()
            
            current = components['tag_filter'].currentText()
            components['tag_filter'].clear()
            components['tag_filter'].addItem("所有标签")
            
            # 按类别分组添加标签
            categories = {}
            for tag in tags:
                cat = tag['category'] or "未分类"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(tag['name'])
            
            # 添加标签
            for category, tag_names in sorted(categories.items()):
                for name in sorted(tag_names):
                    components['tag_filter'].addItem(name)
            
            # 恢复之前的选择
            index = components['tag_filter'].findText(current)
            if index >= 0:
                components['tag_filter'].setCurrentIndex(index)
            
            # 调整下拉框宽度以适应内容
            components['tag_filter'].adjustSize()
            
        except Exception as e:
            print(f"更新标签过滤器失败: {str(e)}")

    def _show_tag_manager(self):
        """显示标签管理对话框"""
        dialog = TagManagerDialog(self.ppt_processor.get_image_processor(), self.tab)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新标签过滤器
            self._update_tag_filter()
            # 刷新图片显示
            self._filter_images()

    def _show_image_context_menu(self, pos):
        """显示图片右键菜单"""
        components = self.ui.get_components()
        item = components['image_grid'].itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self.tab)
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
            
            # 添加其他菜单项
            menu.addSeparator()
            
            find_ppt_action = menu.addAction("打开所在文件夹")
            find_ppt_action.triggered.connect(lambda: self._open_image_folder(item))
            
            copy_action = menu.addAction("复制图片")
            copy_action.triggered.connect(lambda: self._copy_image(item))
            
            menu.exec(components['image_grid'].mapToGlobal(pos))

    def _open_ppt_file(self, ppt_path: str):
        """打开PPT文件"""
        if not Path(ppt_path).exists():
            QMessageBox.warning(self.tab, "警告", "PPT文件已不存在")
            return
        
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
            QMessageBox.warning(self.tab, "警告", "图片文件已不存在")
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
            QMessageBox.warning(self.tab, "警告", "图片文件已不存在")
            return
        
        try:
            # 使用PIL打开图片以检查格式
            with Image.open(image_path) as pil_img:
                # 如果PNG且有透明通道
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
            QMessageBox.critical(self.tab, "错误", f"复制图片时出错：{str(e)}")

    def _batch_process_tags(self):
        """批量处理图片标签"""
        try:
            image_processor = self.ppt_processor.get_image_processor()
            if not image_processor.clip_available:
                QMessageBox.warning(
                    self.tab,
                    "功能不可用",
                    "标签识别功能需要安装额外的库。\n"
                    "请运行: pip install transformers torch torchvision"
                )
                return
            
            reply = QMessageBox.question(
                self.tab,
                "确认",
                "是否要对所有图片进行标签识别？这可能需要一些间。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 显示进度条
                components = self.ui.get_components()
                components['image_progress_bar'].setVisible(True)
                components['image_progress_bar'].setValue(0)
                
                # 创建进度对话框
                progress_dialog = QProgressDialog("正在处理图片标签...", "取消", 0, 100, self.tab)
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
                        self.tab,
                        "完成",
                        f"标签处理完成，共处理 {processed} 张图片"
                    )
                    # 刷新标签过滤器
                    self._update_tag_filter()
                    # 刷新显示
                    self._filter_images()
                else:
                    QMessageBox.warning(
                        self.tab,
                        "提示",
                        "没有处理任何图片，请确保已添加标签"
                    )
                
        except Exception as e:
            QMessageBox.critical(self.tab, "错误", f"批量处理标签失败：{str(e)}")
        finally:
            components = self.ui.get_components()
            components['image_progress_bar'].setVisible(False)

    def _add_ppt_source(self):
        """添加PPT文件源文件夹"""
        components = self.ui.get_components()
        folder_path = QFileDialog.getExistingDirectory(self.tab, "选择PPT文件夹")
        if folder_path:
            try:
                # 检查是否已经添加过
                for row in range(components['source_table'].rowCount()):
                    if components['source_table'].item(row, 0).text() == folder_path:
                        QMessageBox.warning(self.tab, "警告", "该文件夹已经添加过了")
                        return
                
                # 添加到表格
                row = components['source_table'].rowCount()
                components['source_table'].insertRow(row)
                components['source_table'].setItem(row, 0, QTableWidgetItem(folder_path))
                components['source_table'].setItem(row, 1, QTableWidgetItem("未索引"))
                
                # 保存到数据库
                image_processor = self.ppt_processor.get_image_processor()
                image_processor.add_ppt_source(folder_path)
                
                # 更新状态
                self._scan_ppt_source()
                
            except Exception as e:
                QMessageBox.critical(self.tab, "错误", f"添加文件夹时出错：{str(e)}")
                # 回滚UI更改
                if row is not None:
                    components['source_table'].removeRow(row)

    def _remove_ppt_source(self):
        """删除选中的PPT文件源"""
        components = self.ui.get_components()
        selected_rows = set(item.row() for item in components['source_table'].selectedItems())
        if not selected_rows:
            QMessageBox.information(self.tab, "提示", "请选择要删除的文件夹")
            return
        
        try:
            # 从后向前删除行，避免索引变化
            for row in sorted(selected_rows, reverse=True):
                folder_path = components['source_table'].item(row, 0).text()
                components['source_table'].removeRow(row)
                
                # 从数据库中删除
                image_processor = self.ppt_processor.get_image_processor()
                image_processor.remove_ppt_source(folder_path)
            
            # 更新状态
            self._scan_ppt_source()
            
        except Exception as e:
            QMessageBox.critical(self.tab, "错误", f"删除文件夹时出错：{str(e)}")

    def _browse_image_lib(self):
        """选择图片库位置"""
        components = self.ui.get_components()
        folder_path = QFileDialog.getExistingDirectory(self.tab, "选择图片库位置")
        if folder_path:
            try:
                # 检查文件夹权限
                test_file = Path(folder_path) / '.test'
                try:
                    test_file.touch()
                    test_file.unlink()
                except Exception:
                    QMessageBox.warning(
                        self.tab,
                        "警告",
                        "选择的文件夹没有写入权限，请选择其他位置或以管理员身份运行"
                    )
                    return
                
                components['image_lib_path'].setText(folder_path)
                # 保存设置
                image_processor = self.ppt_processor.get_image_processor()
                image_processor.save_setting('image_lib_path', folder_path)
                
            except Exception as e:
                QMessageBox.critical(self.tab, "错误", f"设置图片库位置时出错：{str(e)}")

    def _extract_and_index(self):
        """提取图片并建立索引"""
        components = self.ui.get_components()
        if not components['image_lib_path'].text():
            QMessageBox.warning(self.tab, "警告", "请先选择图片库位置")
            return
        
        if components['source_table'].rowCount() == 0:
            QMessageBox.warning(self.tab, "警告", "请先添加PPT文件夹")
            return
        
        try:
            # 创建进度对话框
            progress_dialog = QProgressDialog("正在扫描PPT文件...", "取消", 0, 100, self.tab)
            progress_dialog.setWindowTitle("提取图片")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setAutoClose(True)
            
            def update_progress(current, total, message=""):
                if progress_dialog.wasCanceled():
                    return False
                
                progress = int((current / total) * 100)
                progress_dialog.setValue(progress)
                if message:
                    progress_dialog.setLabelText(message)
                QApplication.processEvents()
                return True
            
            # 开始处理
            image_processor = self.ppt_processor.get_image_processor()
            total_images = 0
            total_ppts = 0
            
            # 处理每个源文件夹
            for row in range(components['source_table'].rowCount()):
                folder_path = components['source_table'].item(row, 0).text()
                
                # 更新状态
                components['source_table'].setItem(
                    row, 1,
                    QTableWidgetItem("正在扫描...")
                )
                
                try:
                    # 提取图片
                    extracted = image_processor.extract_images_from_folder(
                        folder_path,
                        components['image_lib_path'].text(),
                        progress_callback=update_progress
                    )
                    
                    total_images += extracted['images']
                    total_ppts += extracted['ppts']
                    
                    # 更新状态
                    components['source_table'].setItem(
                        row, 1,
                        QTableWidgetItem(f"已处理 {extracted['ppts']} 个PPT")
                    )
                    
                except Exception as e:
                    print(f"处理文件夹 {folder_path} 时出错: {str(e)}")
                    components['source_table'].setItem(
                        row, 1,
                        QTableWidgetItem("处理失败")
                    )
            
            # 关闭进度对话框
            progress_dialog.close()
            
            # 更新数据库状态
            components['db_status_label'].setText(
                f"数据库状态: 已处理 {total_ppts} 个PPT，提取 {total_images} 张图片"
            )
            
            # 刷新图片显示
            self._display_database_images()
            
            QMessageBox.information(
                self.tab,
                "完成",
                f"索引建立完成\n处理了 {total_ppts} 个PPT文件\n提取了 {total_images} 张图片"
            )
            
        except Exception as e:
            QMessageBox.critical(self.tab, "错误", f"提取图片时出错：{str(e)}")
        finally:
            # 确保进度条被隐藏
            components['image_progress_bar'].setVisible(False)
            if 'progress_dialog' in locals():
                progress_dialog.close()

    def _rebuild_database(self):
        """重建图片数据库"""
        components = self.ui.get_components()
        if not components['image_lib_path'].text():
            QMessageBox.warning(self.tab, "警告", "请先选择图片库位置")
            return
        
        reply = QMessageBox.question(
            self.tab,
            "确认重建",
            "重建数据库将清除所有现有索引，确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 获取图片处理器
                image_processor = self.ppt_processor.get_image_processor()
                
                # 清空数据库
                image_processor.clear_database()
                
                # 重新建立索引
                self._extract_and_index()
                
            except Exception as e:
                QMessageBox.critical(self.tab, "错误", f"重建数据库时出错：{str(e)}")

    def _scan_ppt_source(self):
        """扫描并更新PPT文件源"""
        components = self.ui.get_components()
        if components['source_table'].rowCount() == 0:
            QMessageBox.information(self.tab, "提示", "请先添加PPT文件夹")
            return
        
        try:
            # 显示进度条
            components['image_progress_bar'].setVisible(True)
            components['image_progress_bar'].setMaximum(components['source_table'].rowCount())
            components['image_progress_bar'].setValue(0)
            
            total_ppts = 0
            for row in range(components['source_table'].rowCount()):
                folder_path = components['source_table'].item(row, 0).text()
                
                # 统计PPT文件数量
                ppt_count = sum(1 for f in Path(folder_path).rglob('*.ppt*')
                              if not f.name.startswith('~$'))
                
                # 更新状态
                status_item = QTableWidgetItem(f"已找到 {ppt_count} 个PPT")
                components['source_table'].setItem(row, 1, status_item)
                
                total_ppts += ppt_count
                components['image_progress_bar'].setValue(row + 1)
            
            # 更新数据库状态
            components['db_status_label'].setText(f"数据库状态: 共发现 {total_ppts} 个PPT文件")
            
        except Exception as e:
            QMessageBox.critical(self.tab, "错误", f"扫描文件夹时出错：{str(e)}")
        finally:
            components['image_progress_bar'].setVisible(False)

    def add_cleanup_handler(self, handler):
        """添加清理处理器"""
        self.cleanup_handlers.append(handler)

    def cleanup(self):
        """清理资源"""
        try:
            # 停止加载线程
            self.is_running = False
            
            # 清理图片缓存
            components = self.ui.get_components()
            components['image_grid'].clear()
            self.loaded_images.clear()
            
            # 执行所有注册的清理处理器
            for handler in self.cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    print(f"执行清理处理器时出错: {str(e)}")
            
            # 清理进度条
            components['image_progress_bar'].setVisible(False)
            
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")