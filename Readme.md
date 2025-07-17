# 文件内容搜索工具

一个基于 PyQt5 的桌面应用程序，用于快速索引和搜索本地文件系统中的文本内容。

## 特性

- **高效索引**: 使用 SQLite 数据库存储文件元数据和内容，支持 FTS5 全文搜索以提高查询速度。
- **智能过滤**: 可配置跳过特定目录、文件扩展名和过大文件，避免索引不必要的内容。
- **关键词搜索**: 支持普通关键词搜索和正则表达式搜索。
- **结果高亮**: 搜索结果中高亮显示匹配的关键词。
- **VSCode 集成**: 双击搜索结果可在 VSCode 中打开文件并定位到精确行。
- **索引管理**: 提供清空索引、刷新索引信息等功能。
- **统计信息**: 显示已索引文件数量、总大小、文件类型分布和索引压缩率。

## 截图

<!-- 在这里可以添加应用程序的截图 -->

## 徽章

![Python Version](https://img.shields.io/badge/Python-3.x-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![GitHub stars](https://img.shields.io/github/stars/GHeillcoat/file-search-tool?style=social)
![GitHub forks](https://img.shields.io/github/forks/GHeillcoat/file-search-tool?style=social)
![GitHub issues](https://img.shields.io/github/issues/GHeillcoat/file-search-tool)
![GitHub pull requests](https://img.shields.io/github/issues-pr/GHeillcoat/file-search-tool)

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/GHeillcoat/file-search-tool.git
cd file-search-tool
```

### 2. 创建虚拟环境并安装依赖

建议使用虚拟环境来管理项目依赖。

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install PyQt5
```

### 3. 运行应用程序

```bash
python file_search_app.py
```

## 构建可执行文件

你可以使用 [PyInstaller](https://pyinstaller.org/) 将应用程序打包成独立的可执行文件。

### 1. 安装 PyInstaller

确保你的虚拟环境已激活。

```bash
pip install pyinstaller
```

### 2. 打包应用程序

在项目根目录下运行以下命令：

```bash
pyinstaller --noconfirm --onefile --windowed --add-data "file_index.db;." file_search_app.py
```

- `--noconfirm`: 不询问，直接覆盖旧的 dist/ 和 build/ 目录。
- `--onefile`: 将所有内容打包成一个独立的可执行文件。
- `--windowed` 或 `--noconsole`: 对于 GUI 应用程序，不显示命令行窗口。
- `--add-data "file_index.db;."`: 将 `file_index.db` 文件添加到可执行文件的根目录。如果你的数据库文件在其他位置，请相应调整路径。

### 3. 查找可执行文件

打包完成后，可执行文件将在 `dist/` 目录下生成。例如，在 Windows 上可能是 `dist\file_search_app.exe`。

## 许可证

本项目采用 MIT 许可证。详见 [`LICENSE`](LICENSE) 文件。