import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QStatusBar,
    QMessageBox, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QStyledItemDelegate, QStyle, QGroupBox, QTextEdit,
    QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QTextDocument, QPalette
from file_indexer import FileIndexer

import subprocess
import platform


class FileSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件内容搜索工具")
        self.setGeometry(100, 100, 1000, 700)
        self.init_ui()
        self.load_index_info()

        # 检查VSCode是否可用
        if self.check_vscode_availability():
            self.status_bar.showMessage("准备就绪 - VSCode已检测到")
        else:
            self.status_bar.showMessage("准备就绪 - 未检测到VSCode，将使用默认程序打开文件")

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 搜索标签页
        search_tab = QWidget()
        search_layout = QVBoxLayout()
        
        # 文件夹选择部分
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("目标文件夹:")
        self.folder_path_input = QLineEdit()
        self.folder_path_input.setPlaceholderText("请选择要搜索的文件夹")
        self.select_folder_button = QPushButton("选择文件夹")
        self.select_folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path_input)
        folder_layout.addWidget(self.select_folder_button)
        search_layout.addLayout(folder_layout)

        # 搜索关键词部分
        search_control_layout = QHBoxLayout()
        self.search_label = QLabel("搜索关键词:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入搜索关键词 (支持正则表达式)")
        self.search_input.returnPressed.connect(self.start_search)  # 回车触发搜索
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.start_search)
        self.use_regex_checkbox = QCheckBox("使用正则表达式")
        search_control_layout.addWidget(self.search_label)
        search_control_layout.addWidget(self.search_input)
        search_control_layout.addWidget(self.use_regex_checkbox)
        search_control_layout.addWidget(self.search_button)
        search_layout.addLayout(search_control_layout)

        # 结果显示区域
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["文件/行号", "内容"])
        self.results_tree.setColumnWidth(0, 300)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.itemDoubleClicked.connect(self.open_in_vscode)
        self.results_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_context_menu)
        search_layout.addWidget(self.results_tree)
        
        search_tab.setLayout(search_layout)
        self.tab_widget.addTab(search_tab, "搜索")
        
        # 索引管理标签页
        index_tab = QWidget()
        index_layout = QVBoxLayout()
        
        


        # 索引操作按钮
        index_button_layout = QHBoxLayout()
        self.create_index_button = QPushButton("创建/更新索引")
        self.create_index_button.clicked.connect(self.start_indexing)
        self.clear_index_button = QPushButton("清空索引")
        self.clear_index_button.clicked.connect(self.clear_index_data)
        self.refresh_info_button = QPushButton("刷新信息")
        self.refresh_info_button.clicked.connect(self.load_index_info)
        index_button_layout.addWidget(self.create_index_button)
        index_button_layout.addWidget(self.clear_index_button)
        index_button_layout.addWidget(self.refresh_info_button)
        index_button_layout.addStretch()
        index_layout.addLayout(index_button_layout)
        
        # 索引设置
        settings_group = QGroupBox("索引设置")
        settings_layout = QVBoxLayout()
        
        # 最大文件大小设置
        max_size_layout = QHBoxLayout()
        max_size_layout.addWidget(QLabel("最大文件大小 (MB):"))
        self.max_file_size_spin = QSpinBox()
        self.max_file_size_spin.setMinimum(1)
        self.max_file_size_spin.setMaximum(100)
        self.max_file_size_spin.setValue(5)
        self.max_file_size_spin.setSuffix(" MB")
        max_size_layout.addWidget(self.max_file_size_spin)
        max_size_layout.addStretch()
        settings_layout.addLayout(max_size_layout)
        
        settings_group.setLayout(settings_layout)
        index_layout.addWidget(settings_group)
        
        # 索引信息显示
        info_group = QGroupBox("索引信息")
        info_layout = QVBoxLayout()
        
        # 基本信息
        self.index_info_text = QTextEdit()
        self.index_info_text.setReadOnly(True)
        self.index_info_text.setMaximumHeight(150)
        info_layout.addWidget(self.index_info_text)
        
        # 文件类型统计表格
        self.file_type_table = QTableWidget()
        self.file_type_table.setColumnCount(3)
        self.file_type_table.setHorizontalHeaderLabels(["文件类型", "数量", "总大小"])
        self.file_type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        info_layout.addWidget(QLabel("文件类型分布:"))
        info_layout.addWidget(self.file_type_table)
        
        info_group.setLayout(info_layout)
        index_layout.addWidget(info_group)
        
        # 索引进度日志
        log_group = QGroupBox("索引日志")
        log_layout = QVBoxLayout()
        self.index_log_text = QTextEdit()
        self.index_log_text.setReadOnly(True)
        log_layout.addWidget(self.index_log_text)
        log_group.setLayout(log_layout)
        index_layout.addWidget(log_group)
        
        index_tab.setLayout(index_layout)
        self.tab_widget.addTab(index_tab, "索引管理")
        
        main_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        self.setLayout(main_layout)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder_path:
            self.folder_path_input.setText(folder_path)
            self.status_bar.showMessage(f"已选择文件夹: {folder_path}")

    def start_indexing(self):
        folder_path = self.folder_path_input.text()
        if not folder_path or not os.path.isdir(folder_path):
            QMessageBox.warning(self, "错误", "请选择一个有效的文件夹。")
            return

        # 清空日志
        self.index_log_text.clear()
        self.status_bar.showMessage("正在创建索引...")
        self.results_tree.clear()
        self.create_index_button.setEnabled(False)
        self.search_button.setEnabled(False)
        self.clear_index_button.setEnabled(False)

        # 获取设置
        max_file_size = self.max_file_size_spin.value() * 1024 * 1024

        self.indexer_thread = QThread()
        self.file_indexer = FileIndexer()
        self.file_indexer.max_file_size = max_file_size  # 设置最大文件大小
        self.file_indexer.moveToThread(self.indexer_thread)

        self.file_indexer.indexing_progress.connect(self.update_index_log)
        self.file_indexer.indexing_finished.connect(self.indexing_finished)
        self.file_indexer.indexing_error.connect(self.indexing_error)

        self.indexer_thread.started.connect(lambda: self.file_indexer.index_folder(folder_path))
        self.indexer_thread.start()

    def update_index_log(self, message):
        """更新索引日志"""
        self.index_log_text.append(message)
        # 自动滚动到底部
        scrollbar = self.index_log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 同时更新状态栏
        self.status_bar.showMessage(message)

    def indexing_finished(self, count):
        self.status_bar.showMessage(f"索引创建完成。已索引 {count} 个文件。")
        self.create_index_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.clear_index_button.setEnabled(True)
        self.indexer_thread.quit()
        self.indexer_thread.wait()
        
        # 自动刷新索引信息
        self.load_index_info()

    def indexing_error(self, message):
        self.index_log_text.append(f"错误: {message}")
        QMessageBox.critical(self, "索引错误", message)
        self.status_bar.showMessage("索引创建失败。")
        self.create_index_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.clear_index_button.setEnabled(True)
        self.indexer_thread.quit()
        self.indexer_thread.wait()

    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.results_tree.itemAt(position)
        if item and item.parent() is not None:  # 只对行项目显示菜单
            from PyQt5.QtWidgets import QMenu, QAction
            
            menu = QMenu(self)
            
            # 在VSCode中打开
            open_vscode_action = QAction("在VSCode中打开", self)
            open_vscode_action.triggered.connect(lambda: self.open_in_vscode(item, 0))
            menu.addAction(open_vscode_action)
            
            # 用默认程序打开
            open_default_action = QAction("用默认程序打开", self)
            open_default_action.triggered.connect(lambda: self.open_file_with_default(item.parent().toolTip(0)))
            menu.addAction(open_default_action)
            
            # 复制文件路径
            copy_path_action = QAction("复制文件路径", self)
            copy_path_action.triggered.connect(lambda: QApplication.clipboard().setText(item.parent().toolTip(0)))
            menu.addAction(copy_path_action)
            
            # 复制行内容
            copy_content_action = QAction("复制行内容", self)
            copy_content_action.triggered.connect(lambda: QApplication.clipboard().setText(item.data(1, Qt.UserRole) or item.text(1)))
            menu.addAction(copy_content_action)
            
            menu.exec_(self.results_tree.mapToGlobal(position))

    def load_index_info(self):
        """加载并显示索引信息"""
        indexer = FileIndexer()
        info = indexer.get_index_info()
        
        if info:
            # 显示基本信息
            info_text = f"""索引统计信息：
- 已索引文件数：{info['file_count']} 个
- 文件总大小：{info['total_size_str']}
- 索引文件大小：{info['index_size_str']}
- 压缩率：{info['compression_ratio']}
"""
            self.index_info_text.setText(info_text)
            
            # 显示文件类型分布
            self.file_type_table.setRowCount(len(info['file_types']))
            for i, (ext, count, size) in enumerate(info['file_types']):
                self.file_type_table.setItem(i, 0, QTableWidgetItem(ext or "无扩展名"))
                self.file_type_table.setItem(i, 1, QTableWidgetItem(str(count)))
                self.file_type_table.setItem(i, 2, QTableWidgetItem(indexer.format_size(size or 0)))
        else:
            self.index_info_text.setText("暂无索引信息")
            self.file_type_table.setRowCount(0)

    def start_search(self):
        folder_path = self.folder_path_input.text()
        keyword = self.search_input.text()

        if not folder_path or not os.path.isdir(folder_path):
            QMessageBox.warning(self, "错误", "请选择一个有效的文件夹。")
            return

        if not keyword:
            QMessageBox.warning(self, "错误", "请输入搜索关键词。")
            return

        self.status_bar.showMessage(f"正在搜索 '{keyword}'...")
        self.results_tree.clear()
        self.create_index_button.setEnabled(False)
        self.search_button.setEnabled(False)

        self.search_thread = QThread()
        self.file_indexer = FileIndexer()
        self.file_indexer.moveToThread(self.search_thread)

        self.file_indexer.indexing_progress.connect(self.update_status)
        self.file_indexer.indexing_error.connect(self.search_error)

        self.search_thread.started.connect(lambda: self._run_search(keyword, folder_path))
        self.search_thread.start()

    def update_status(self, message):
        self.status_bar.showMessage(message)

    def _run_search(self, keyword, folder_path):
        use_regex = self.use_regex_checkbox.isChecked()
        results = self.file_indexer.search_content(keyword, folder_path, use_regex)
        self.search_finished(results, keyword)

    def highlight_keyword(self, text, keyword, use_regex=False):
        """高亮显示匹配的关键词"""
        if not keyword:
            return text
        
        # 转义HTML特殊字符
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 转义特殊字符，避免在非正则模式下出错
        if not use_regex:
            keyword = re.escape(keyword)
        
        try:
            # 使用HTML标签高亮显示
            highlighted = re.sub(
                f'({keyword})', 
                r'<span style="background-color: yellow; font-weight: bold;">\1</span>', 
                text, 
                flags=re.IGNORECASE if not use_regex else 0
            )
            return highlighted
        except:
            return text

    def search_finished(self, results, keyword):
        if not results:
            root_item = QTreeWidgetItem(self.results_tree)
            root_item.setText(0, "未找到匹配项")
            root_item.setText(1, "")
        else:
            # 如果结果太多，限制显示数量
            max_display = 1000
            total_results = len(results)
            
            if total_results > max_display:
                # 显示警告
                warning_item = QTreeWidgetItem(self.results_tree)
                warning_item.setText(0, f"警告：找到 {total_results} 个结果，仅显示前 {max_display} 个")
                warning_item.setForeground(0, Qt.red)
                font = QFont()
                font.setBold(True)
                warning_item.setFont(0, font)
                
                results = results[:max_display]
            
            # 按文件分组结果
            file_groups = {}
            for result in results:
                file_path = result["file_path"]
                if file_path not in file_groups:
                    file_groups[file_path] = []
                file_groups[file_path].append(result)
            
            # 添加到树形控件
            for file_path, file_results in file_groups.items():
                # 创建文件节点
                file_item = QTreeWidgetItem(self.results_tree)
                file_item.setText(0, os.path.basename(file_path))
                file_item.setText(1, f"({len(file_results)} 个匹配)")
                file_item.setToolTip(0, file_path)
                
                # 设置文件节点字体为粗体
                font = QFont()
                font.setBold(True)
                file_item.setFont(0, font)
                
                # 添加行结果
                for result in file_results:
                    line_item = QTreeWidgetItem(file_item)
                    line_item.setText(0, f"行 {result['line_number']}")
                    
                    # 高亮显示匹配的文本
                    use_regex = self.use_regex_checkbox.isChecked()
                    highlighted_text = self.highlight_keyword(
                        result['line_content'].strip(), 
                        keyword, 
                        use_regex
                    )
                    
                    # 设置富文本显示
                    line_item.setData(1, Qt.DisplayRole, "")
                    line_item.setData(1, Qt.UserRole, highlighted_text)
                    
                # 只展开前10个文件节点，避免界面卡顿
                if list(file_groups.keys()).index(file_path) < 10:
                    file_item.setExpanded(True)
            
            # 自定义绘制以显示HTML
            self.results_tree.setItemDelegate(HTMLDelegate())
        
        self.status_bar.showMessage(f"搜索完成。找到 {total_results if 'total_results' in locals() else len(results)} 个匹配项。")
        self.create_index_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.search_thread.quit()
        self.search_thread.wait()

    def open_in_vscode(self, item, column):
        """双击打开VSCode并定位到指定行"""
        try:
            # 检查是否是行项目（有父项目的才是行项目）
            if item.parent() is None:
                # 这是文件节点，不处理
                return
            
            # 获取文件路径（从父节点的tooltip）
            file_item = item.parent()
            file_path = file_item.toolTip(0)
            
            # 获取行号（从当前项的文本中提取）
            line_text = item.text(0)  # 格式如 "行 123"
            if line_text.startswith("行 "):
                try:
                    line_number = int(line_text.split(" ")[1])
                except (IndexError, ValueError):
                    line_number = 1
            else:
                line_number = 1
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "文件不存在", f"文件不存在：{file_path}")
                return
            
            # 尝试打开VSCode
            if self.open_file_in_vscode(file_path, line_number):
                self.status_bar.showMessage(f"已在VSCode中打开: {os.path.basename(file_path)}:{line_number}")
            else:
                # 如果VSCode不可用，尝试其他编辑器或默认程序
                self.open_file_with_default(file_path)
                
        except Exception as e:
            QMessageBox.critical(self, "打开文件失败", f"打开文件时出错：{str(e)}")

    def open_file_in_vscode(self, file_path, line_number=1):
        """使用VSCode打开文件并定位到指定行"""
        try:
            # VSCode命令行参数：--goto 文件路径:行号:列号
            goto_arg = f"{file_path}:{line_number}:1"
            
            # 根据操作系统选择合适的命令
            system = platform.system().lower()
            
            if system == "windows":
                # Windows下尝试不同的VSCode命令和常见安装路径
                commands = [
                    "code",
                    "code.exe",
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft VS Code", "bin", "code.cmd"),
                    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")), "Programs", "Microsoft VS Code", "bin", "code.cmd")
                ]
            elif system == "darwin":  # macOS
                commands = [
                    "code",
                    "/usr/local/bin/code",
                    "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
                ]
            else:  # Linux和其他Unix系统
                commands = [
                    "code",
                    "/usr/bin/code",
                    "/usr/local/bin/code"
                ]
            
            # 尝试每个可能的命令
            for cmd in commands:
                try:
                    # 使用subprocess.run而不是Popen，这样可以更好地处理错误
                    result = subprocess.run(
                        [cmd, "--goto", goto_arg],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW if system == "windows" else 0
                    )
                    
                    # 如果命令成功执行（返回码为0或1都算成功，因为VSCode有时返回1）
                    if result.returncode in [0, 1]:
                        return True
                        
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            return False
            
        except Exception:
            return False

    def open_file_with_default(self, file_path):
        """使用系统默认程序打开文件"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                # Windows使用start命令
                subprocess.run(["start", "", file_path], shell=True, check=True)
            elif system == "darwin":  # macOS
                # macOS使用open命令
                subprocess.run(["open", file_path], check=True)
            else:  # Linux
                # Linux使用xdg-open命令
                subprocess.run(["xdg-open", file_path], check=True)
            
            self.status_bar.showMessage(f"已使用默认程序打开: {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件：{str(e)}\n\n请检查VSCode是否已安装并添加到PATH环境变量中。")

    def check_vscode_availability(self):
        """检查VSCode是否可用"""
        # 尝试使用 open_file_in_vscode 中的逻辑来检查
        # 传入一个虚拟文件路径，因为我们只关心命令是否能执行
        # 实际不会打开文件
        return self.open_file_in_vscode("dummy_file.txt", 1)
    def clear_index_data(self):
        reply = QMessageBox.question(self, '清空索引', '确定要清空所有索引数据吗？此操作不可逆。',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.status_bar.showMessage("正在清空索引...")
            self.create_index_button.setEnabled(False)
            self.search_button.setEnabled(False)
            self.clear_index_button.setEnabled(False)

            self.indexer_thread = QThread()
            self.file_indexer = FileIndexer()
            self.file_indexer.moveToThread(self.indexer_thread)

            self.file_indexer.indexing_progress.connect(self.update_status)
            self.file_indexer.indexing_error.connect(self.indexing_error)

            self.indexer_thread.started.connect(self.file_indexer.clear_index)
            self.indexer_thread.finished.connect(self.clear_index_finished)
            self.indexer_thread.start()

    def clear_index_finished(self):
        self.status_bar.showMessage("索引已清空。")
        self.create_index_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.clear_index_button.setEnabled(True)
        self.indexer_thread.quit()
        self.indexer_thread.wait()
        
        # 刷新索引信息
        self.load_index_info()

    def search_error(self, message):
        QMessageBox.critical(self, "搜索错误", message)
        self.status_bar.showMessage("搜索失败。")
        self.create_index_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.clear_index_button.setEnabled(True)
        self.search_thread.quit()
        self.search_thread.wait()


# 自定义委托类，用于显示HTML格式的文本
class HTMLDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 1:  # 只处理第二列（内容列）
            html_text = index.data(Qt.UserRole)
            if html_text:
                painter.save()
                
                # 创建文本文档
                doc = QTextDocument()
                doc.setHtml(html_text)
                doc.setTextWidth(option.rect.width())
                
                # 处理选中状态
                if option.state & QStyle.State_Selected:
                    painter.fillRect(option.rect, option.palette.highlight())
                    # 设置文本颜色为高亮文本颜色
                    palette = option.palette
                    doc.setDefaultStyleSheet(
                        f"body {{ color: {palette.color(QPalette.HighlightedText).name()}; }}"
                    )
                
                # 绘制文本
                painter.translate(option.rect.x(), option.rect.y())
                doc.drawContents(painter)
                
                painter.restore()
                return
        
        # 其他情况使用默认绘制
        super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        if index.column() == 1:
            html_text = index.data(Qt.UserRole)
            if html_text:
                doc = QTextDocument()
                doc.setHtml(html_text)
                doc.setTextWidth(option.rect.width() if option.rect.width() > 0 else 300)
                return QSize(int(doc.idealWidth()), int(doc.size().height()))
        
        return super().sizeHint(option, index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileSearchApp()
    window.show()
    sys.exit(app.exec_())