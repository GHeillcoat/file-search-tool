import os
import sqlite3
import mimetypes
import hashlib
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class FileIndexer(QObject):
    indexing_progress = pyqtSignal(str)
    indexing_finished = pyqtSignal(int)
    indexing_error = pyqtSignal(str)
    

    def __init__(self, db_path="file_index.db"):
        super().__init__()
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.fts_enabled = False
        
        # 支持的文本文件扩展名（白名单）
        self.text_extensions = {
            # 编程语言源代码
            '.py', '.pyw', '.pyx', '.pyi',  # Python
            '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',  # JavaScript/TypeScript
            '.java', '.class',  # Java
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',  # C/C++
            '.cs', '.vb', '.fs',  # .NET languages
            '.go',  # Go
            '.rs',  # Rust
            '.php', '.phtml',  # PHP
            '.rb', '.erb',  # Ruby
            '.swift',  # Swift
            '.kt', '.kts',  # Kotlin
            '.scala',  # Scala
            '.r', '.R',  # R
            '.m', '.mm',  # Objective-C
            '.lua',  # Lua
            '.pl', '.pm',  # Perl
            '.sh', '.bash', '.zsh', '.fish',  # Shell
            '.bat', '.cmd', '.ps1',  # Windows scripts
            
            # 标记语言和配置文件
            '.html', '.htm', '.xhtml',  # HTML
            '.xml', '.xsl', '.xslt',  # XML
            '.css', '.scss', '.sass', '.less',  # CSS
            '.json', '.jsonc',  # JSON
            '.yaml', '.yml',  # YAML
            '.toml',  # TOML
            '.ini', '.cfg', '.conf', '.config',  # Config files
            '.properties',  # Properties files
            '.env', '.env.example',  # Environment files
            
            # 文档和文本文件
            '.txt', '.text',  # Plain text
            '.md', '.markdown', '.mdown',  # Markdown
            '.rst',  # reStructuredText
            '.tex', '.latex',  # LaTeX
            '.org',  # Org mode
            '.log',  # Log files
            '.csv', '.tsv',  # Tabular data
            
            # 构建和项目文件
            '.makefile', '.mk',  # Makefile
            '.gradle',  # Gradle
            '.cmake',  # CMake
            '.dockerfile',  # Docker
            '.gitignore', '.gitattributes',  # Git
            '.editorconfig',  # Editor config
            
            # 其他开发相关
            '.sql',  # SQL
            '.graphql', '.gql',  # GraphQL
            '.proto',  # Protocol Buffers
            '.vue',  # Vue.js
            '.svelte',  # Svelte
        }
        
        # 需要跳过的文件扩展名（黑名单）
        self.skip_extensions = {
            # 可执行文件和库
            '.exe', '.dll', '.so', '.dylib', '.sys', '.com', '.app',
            '.deb', '.rpm', '.dmg', '.pkg', '.msi','.apk',
            
            # 编译后的文件
            '.o', '.obj', '.pyc', '.pyo', '.pyd', '.class', '.jar', '.war',
            '.beam', '.elc', '.out', '.a', '.lib',
            
            # 压缩文件
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz',
            '.iso', '.cab',
            
            # 图片文件
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',
            '.tiff', '.tif', '.psd', '.ai', '.eps', '.raw',
            
            # 音视频文件
            '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
            '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
            '.mpg', '.mpeg', '.3gp', '.m4v',
            
            # Office和文档
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods',
            '.odp', '.pdf', '.epub', '.mobi',
            
            # 字体文件
            '.ttf', '.otf', '.woff', '.woff2', '.eot',
            
            # 数据库文件
            '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb',
            
            # 其他二进制文件
            '.bin', '.dat', '.data', '.dump', '.img',
            
            # 模型和数据文件
            '.h5', '.hdf5', '.pkl', '.pickle', '.npy', '.npz',
            '.model', '.weights', '.onnx', '.pb', '.pth', '.pt',
            
            # 临时和缓存文件
            '.tmp', '.temp', '.cache', '.swp', '.swo', '.swn',
            '.bak', '.backup', '.old', '.orig',
        }
        
        # 跳过的目录
        self.skip_dirs = {
            # 版本控制
            '.git', '.svn', '.hg', '.bzr',
            
            # Python
            '__pycache__', '.pytest_cache', '.mypy_cache', '.tox',
            'venv', 'env', '.env', 'virtualenv', '.venv',
            '.eggs', '*.egg-info', 'dist', 'build', 'htmlcov',
            
            # Node.js
            'node_modules', '.npm', '.yarn', '.pnpm-store',
            
            # 前端框架
            '.next', '.nuxt', '.svelte-kit', '.gatsby', '.cache',
            'out', '.output', '.parcel-cache',
            
            # IDE和编辑器
            '.idea', '.vscode', '.vs', '.sublime', '.atom',
            '.settings', '.project', '.classpath',
            
            # 构建输出
            'dist', 'build', 'out', 'target', 'bin', 'obj',
            '.gradle', '.maven',
            
            # 系统和临时
            '.DS_Store', 'Thumbs.db', '.Trash', '$RECYCLE.BIN',
            'tmp', 'temp', 'cache', 'logs',
            
            # 其他
            'vendor', 'packages', '.bundle', 'coverage',
            '.terraform', '.serverless', '.aws-sam',
        }
        
        # 最大文件大小（默认5MB）
        self.max_file_size = 5 * 1024 * 1024

    def connect_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # 启用 WAL 模式以提高性能
            self.cursor.execute("PRAGMA journal_mode=WAL")
            self.cursor.execute("PRAGMA synchronous=NORMAL")
            self.cursor.execute("PRAGMA cache_size=10000")
            self.cursor.execute("PRAGMA temp_store=MEMORY")
            
            self.create_tables()
            return True
        except sqlite3.Error as e:
            self.indexing_error.emit(f"数据库连接或创建失败: {e}")
            return False

    def create_tables(self):
        # 首先检查是否需要升级表结构
        self.cursor.execute("PRAGMA table_info(files)")
        columns = [col[1] for col in self.cursor.fetchall()]
        
        # 如果表存在但缺少新列，则添加它们
        if 'files' in [t[0] for t in self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            if 'file_hash' not in columns:
                self.cursor.execute("ALTER TABLE files ADD COLUMN file_hash TEXT")
                self.indexing_progress.emit("升级数据库：添加 file_hash 列")
            
            if 'modified_time' not in columns:
                self.cursor.execute("ALTER TABLE files ADD COLUMN modified_time REAL")
                self.indexing_progress.emit("升级数据库：添加 modified_time 列")
        
        # 创建或更新文件表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                file_ext TEXT,
                file_hash TEXT,
                modified_time REAL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 检查是否支持 FTS5
        try:
            self.cursor.execute("SELECT fts5_version()")
            # 如果支持 FTS5，创建虚拟表（注意：FTS5 中不需要指定列类型）
            self.cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS file_contents USING fts5(
                    file_id,
                    line_number,
                    content,
                    tokenize = 'porter unicode61'
                )
            """)
            self.fts_enabled = True
            self.indexing_progress.emit("使用 FTS5 全文搜索")
        except sqlite3.Error:
            # 如果不支持 FTS5，使用普通表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    line_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files (id)
                )
            """)
            self.fts_enabled = False
            self.indexing_progress.emit("FTS5 不可用，使用普通搜索")
        
        # 创建索引以提高查询性能
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_ext ON files(file_ext)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash)
        """)
        
        if not self.fts_enabled:
            # 为普通表创建额外的索引
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_contents_file_id ON file_contents(file_id)
            """)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_contents_content ON file_contents(content)
            """)
        
        self.conn.commit()
    def clear_index(self):
        if self.conn:
            self.cursor.execute("DELETE FROM files")
            self.cursor.execute("DELETE FROM file_contents")
            self.conn.commit()
            self.indexing_progress.emit("旧索引已清除。")

    def calculate_file_hash(self, file_path, chunk_size=8192):
        """计算文件的MD5哈希值"""
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    md5_hash.update(chunk)
                    # 对于大文件，只读取前1MB来计算哈希
                    if f.tell() >= 1024 * 1024:
                        break
            return md5_hash.hexdigest()
        except Exception:
            return None

    def should_skip_directory(self, dir_name):
        """检查是否应该跳过该目录"""
        # 检查是否是隐藏目录（除了某些特殊情况）
        if dir_name.startswith('.') and dir_name not in {'.github', '.gitlab'}:
            return True
        
        # 检查是否在跳过列表中
        if dir_name in self.skip_dirs:
            return True
        
        # 检查是否匹配通配符模式
        for pattern in self.skip_dirs:
            if '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(dir_name, pattern):
                    return True
        
        return False

    def should_index_file(self, file_path):
        """判断是否应该索引该文件"""
        file_name = os.path.basename(file_path)
        
        # 跳过隐藏文件
        if file_name.startswith('.') and file_name not in {'.gitignore', '.env', '.env.example', '.editorconfig'}:
            return False, 0, "hidden"
        
        # 检查文件大小
        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return False, file_size, "too_large"
            if file_size == 0:
                return False, 0, "empty"
        except:
            return False, 0, "error"
        
        # 检查文件扩展名
        _, ext = os.path.splitext(file_path.lower())
        
        # 先检查黑名单
        if ext in self.skip_extensions:
            return False, file_size, "skip_ext"
        
        # 再检查白名单
        if ext in self.text_extensions:
            return True, file_size, "text_ext"
        
        # 没有扩展名的文件，尝试通过内容判断
        if not ext:
            # 检查一些常见的无扩展名文本文件
            base_name = os.path.basename(file_path).lower()
            if base_name in {'makefile', 'dockerfile', 'rakefile', 'gemfile', 'pipfile', 'readme', 'license', 'changelog'}:
                return True, file_size, "known_text"
        
        # 尝试通过 MIME 类型判断
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and (mime_type.startswith('text/') or mime_type in {'application/json', 'application/xml'}):
            return True, file_size, "mime_text"
        
        return False, file_size, "unknown"

    def index_file(self, file_path, file_id=None):
        """索引单个文件的内容"""
        try:
            # 如果有旧的file_id，先删除旧内容
            if file_id:
                self.cursor.execute("DELETE FROM file_contents WHERE file_id = ?", (file_id,))
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            _, ext = os.path.splitext(file_path.lower())
            modified_time = os.path.getmtime(file_path)
            file_hash = self.calculate_file_hash(file_path)
            
            if not file_hash:
                return None
            
            # 插入或更新文件记录
            if file_id:
                self.cursor.execute("""
                    UPDATE files 
                    SET file_name = ?, file_size = ?, file_ext = ?, 
                        file_hash = ?, modified_time = ?, indexed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (file_name, file_size, ext, file_hash, modified_time, file_id))
            else:
                self.cursor.execute("""
                    INSERT INTO files (file_path, file_name, file_size, file_ext, file_hash, modified_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_path, file_name, file_size, ext, file_hash, modified_time))
                file_id = self.cursor.lastrowid
            
            # 读取并索引文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                batch_data = []
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过空行和过长的行
                    if line and len(line) < 1000:
                        batch_data.append((file_id, line_num, line))
                        
                        # 批量插入以提高性能
                        if len(batch_data) >= 1000:
                            self.cursor.executemany(
                                "INSERT INTO file_contents (file_id, line_number, content) VALUES (?, ?, ?)",
                                batch_data
                            )
                            batch_data = []
                    
                    # 防止大文件占用过多内存
                    if line_num > 10000:
                        break
                
                # 插入剩余的数据
                if batch_data:
                    self.cursor.executemany(
                        "INSERT INTO file_contents (file_id, line_number, content) VALUES (?, ?, ?)",
                        batch_data
                    )
            
            return file_id
            
        except Exception as e:
            self.indexing_error.emit(f"索引文件失败 {file_path}: {str(e)}")
            return None

    def update_index(self, folder_path):
        """增量更新索引"""
        if not self.connect_db():
            return

        stats = {
            'new': 0,
            'updated': 0,
            'deleted': 0,
            'unchanged': 0,
            'skipped': 0,
            'errors': 0,
            'total_size': 0
        }
        
        # 获取当前索引中的所有文件
        self.cursor.execute("SELECT id, file_path, file_hash, modified_time FROM files WHERE file_path LIKE ?", 
                           (f"{folder_path}%",))
        existing_files = {row[1]: {'id': row[0], 'hash': row[2], 'mtime': row[3]} 
                         for row in self.cursor.fetchall()}
        
        # 用于跟踪处理过的文件
        processed_files = set()
        
        # 开始事务
        self.conn.execute("BEGIN TRANSACTION")
        
        try:
            for root, dirs, files in os.walk(folder_path):
                # 过滤掉不需要的目录
                dirs[:] = [d for d in dirs if not self.should_skip_directory(d)]
                
                # 显示当前处理的目录
                rel_path = os.path.relpath(root, folder_path)
                if rel_path != '.':
                    self.indexing_progress.emit(f"扫描目录: {rel_path}")
                
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    processed_files.add(file_path)
                    
                    # 检查是否应该索引该文件
                    should_index, file_size, reason = self.should_index_file(file_path)
                    
                    if not should_index:
                        stats['skipped'] += 1
                        continue
                    
                    try:
                        # 计算文件哈希和修改时间
                        file_hash = self.calculate_file_hash(file_path)
                        modified_time = os.path.getmtime(file_path)
                        
                        if not file_hash:
                            stats['errors'] += 1
                            continue
                        
                        # 检查文件是否已存在于索引中
                        if file_path in existing_files:
                            existing_info = existing_files[file_path]
                            
                            # 比较哈希值和修改时间
                            if (existing_info['hash'] == file_hash and 
                                abs(existing_info['mtime'] - modified_time) < 1):
                                # 文件未变化
                                stats['unchanged'] += 1
                                self.indexing_progress.emit(f"未变化: {file_name}")
                            else:
                                # 文件已变化，需要更新
                                if self.index_file(file_path, existing_info['id']):
                                    stats['updated'] += 1
                                    stats['total_size'] += file_size
                                    self.indexing_progress.emit(f"已更新: {file_name}")
                                else:
                                    stats['errors'] += 1
                        else:
                            # 新文件
                            if self.index_file(file_path):
                                stats['new'] += 1
                                stats['total_size'] += file_size
                                self.indexing_progress.emit(f"新文件: {file_name}")
                            else:
                                stats['errors'] += 1
                        
                        # 每100个文件提交一次
                        if (stats['new'] + stats['updated']) % 100 == 0:
                            self.conn.commit()
                            self.conn.execute("BEGIN TRANSACTION")
                            
                    except Exception as e:
                        stats['errors'] += 1
                        self.indexing_error.emit(f"处理文件失败 {file_name}: {str(e)}")
            
            # 删除不存在的文件
            for file_path, file_info in existing_files.items():
                if file_path not in processed_files:
                    # 文件已被删除
                    self.cursor.execute("DELETE FROM file_contents WHERE file_id = ?", (file_info['id'],))
                    self.cursor.execute("DELETE FROM files WHERE id = ?", (file_info['id'],))
                    stats['deleted'] += 1
                    self.indexing_progress.emit(f"已删除: {os.path.basename(file_path)}")
            
            # 提交最终事务
            self.conn.commit()
            
            # 优化数据库（仅在有较大变化时）
            if stats['new'] + stats['updated'] + stats['deleted'] > 100:
                self.indexing_progress.emit("正在优化数据库...")
                self.cursor.execute("VACUUM")
                self.cursor.execute("ANALYZE")
            
        except Exception as e:
            self.conn.rollback()
            self.indexing_error.emit(f"更新索引过程出错: {str(e)}")
        finally:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
        
        # 生成统计信息
        total_processed = stats['new'] + stats['updated'] + stats['unchanged']
        self.indexing_progress.emit(
            f"更新完成：新增 {stats['new']} 个，更新 {stats['updated']} 个，"
            f"删除 {stats['deleted']} 个，未变化 {stats['unchanged']} 个，"
            f"跳过 {stats['skipped']} 个，错误 {stats['errors']} 个"
        )
        self.indexing_finished.emit(total_processed)

    def index_folder(self, folder_path):
        """创建新索引（清空旧索引）"""
        if not self.connect_db():
            return

        self.clear_index()
        
        stats = {
            'indexed': 0,
            'skipped': 0,
            'errors': 0,
            'total_size': 0,
            'skip_reasons': {}
        }
        
        # 开始事务
        self.conn.execute("BEGIN TRANSACTION")
        
        try:
            for root, dirs, files in os.walk(folder_path):
                # 过滤掉不需要的目录
                dirs[:] = [d for d in dirs if not self.should_skip_directory(d)]
                
                # 显示当前处理的目录
                rel_path = os.path.relpath(root, folder_path)
                if rel_path != '.':
                    self.indexing_progress.emit(f"扫描目录: {rel_path}")
                
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    # 检查是否应该索引该文件
                    should_index, file_size, reason = self.should_index_file(file_path)
                    
                    if not should_index:
                        stats['skipped'] += 1
                        stats['skip_reasons'][reason] = stats['skip_reasons'].get(reason, 0) + 1
                        continue
                    
                    try:
                        if self.index_file(file_path):
                            stats['indexed'] += 1
                            stats['total_size'] += file_size
                            self.indexing_progress.emit(f"已索引: {file_name}")
                        else:
                            stats['errors'] += 1
                        
                        # 每100个文件提交一次
                        if stats['indexed'] % 100 == 0:
                            self.conn.commit()
                            self.conn.execute("BEGIN TRANSACTION")
                            
                    except Exception as e:
                        stats['errors'] += 1
                        self.indexing_error.emit(f"索引文件失败 {file_name}: {str(e)}")
            
            # 提交最终事务
            self.conn.commit()
            
            # 优化数据库
            self.indexing_progress.emit("正在优化数据库...")
            self.cursor.execute("VACUUM")
            self.cursor.execute("ANALYZE")
            
        except Exception as e:
            self.conn.rollback()
            self.indexing_error.emit(f"索引过程出错: {str(e)}")
        finally:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
        
        # 获取数据库文件大小
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        # 生成详细的统计信息
        skip_info = []
        for reason, count in stats['skip_reasons'].items():
            reason_text = {
                'hidden': '隐藏文件',
                'too_large': '文件过大',
                'empty': '空文件',
                'skip_ext': '二进制/媒体文件',
                'unknown': '未知类型',
                'error': '读取错误'
            }.get(reason, reason)
            skip_info.append(f"{reason_text}: {count}")
        
        self.indexing_progress.emit(
            f"索引完成：已索引 {stats['indexed']} 个文件，"
            f"跳过 {stats['skipped']} 个文件 ({', '.join(skip_info)})，"
            f"错误 {stats['errors']} 个，"
            f"总大小 {self.format_size(stats['total_size'])}，"
            f"索引大小 {self.format_size(db_size)}"
        )
        self.indexing_finished.emit(stats['indexed'])

    def search_content(self, keyword, folder_path=None, use_regex=False):
        if not self.connect_db():
            return []

        results = []
        
        try:
            if use_regex:
                # 正则表达式搜索（较慢）
                import re
                pattern = re.compile(keyword, re.IGNORECASE)
                
                query = """
                    SELECT f.file_path, fc.line_number, fc.content
                    FROM file_contents fc
                    JOIN files f ON fc.file_id = f.id
                """
                params = []
                
                if folder_path:
                    query += " WHERE f.file_path LIKE ?"
                    params.append(f"{folder_path}%")
                
                query += " ORDER BY f.file_path, fc.line_number"
                
                self.cursor.execute(query, params)
                
                for row in self.cursor.fetchall():
                    if pattern.search(row[2]):
                        results.append({
                            "file_path": row[0],
                            "line_number": row[1],
                            "line_content": row[2]
                        })
                        
                        # 限制结果数量
                        if len(results) >= 10000:
                            break
            else:
                if self.fts_enabled:
                    # 使用全文搜索（快速）
                    query = """
                        SELECT f.file_path, fc.line_number, fc.content
                        FROM file_contents fc
                        JOIN files f ON fc.file_id = f.id
                        WHERE fc.content MATCH ?
                    """
                    params = [keyword]
                    
                    if folder_path:
                        query += " AND f.file_path LIKE ?"
                        params.append(f"{folder_path}%")
                    
                    query += " ORDER BY f.file_path, fc.line_number LIMIT 10000"
                else:
                    # 使用 LIKE 搜索（较慢但兼容性好）
                    query = """
                        SELECT f.file_path, fc.line_number, fc.content
                        FROM file_contents fc
                        JOIN files f ON fc.file_id = f.id
                        WHERE fc.content LIKE ?
                    """
                    params = [f"%{keyword}%"]
                    
                    if folder_path:
                        query += " AND f.file_path LIKE ?"
                        params.append(f"{folder_path}%")
                    
                    query += " ORDER BY f.file_path, fc.line_number LIMIT 10000"
                
                self.cursor.execute(query, params)
                
                for row in self.cursor.fetchall():
                    results.append({
                        "file_path": row[0],
                        "line_number": row[1],
                        "line_content": row[2]
                    })
            
        except sqlite3.Error as e:
            self.indexing_error.emit(f"搜索失败: {str(e)}")
        finally:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
        
        return results

    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def get_index_info(self):
        """获取索引信息"""
        if not self.connect_db():
            return None
        
        try:
            info = {}
            
            # 获取文件数量
            self.cursor.execute("SELECT COUNT(*) FROM files")
            info['file_count'] = self.cursor.fetchone()[0]
            
            # 获取文件类型分布
            self.cursor.execute("""
                SELECT file_ext, COUNT(*) as count, SUM(file_size) as total_size
                FROM files
                GROUP BY file_ext
                ORDER BY count DESC
                LIMIT 10
            """)
            info['file_types'] = self.cursor.fetchall()
            
            # 获取总大小
            self.cursor.execute("SELECT SUM(file_size) FROM files")
            total_size = self.cursor.fetchone()[0] or 0
            info['total_size'] = total_size
            info['total_size_str'] = self.format_size(total_size)
            
            # 获取索引大小
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            info['index_size'] = db_size
            info['index_size_str'] = self.format_size(db_size)
            
            # 计算压缩率
            if total_size > 0:
                info['compression_ratio'] = f"{(db_size / total_size * 100):.1f}%"
            else:
                info['compression_ratio'] = "N/A"
            
            # 获取最后索引时间
            self.cursor.execute("SELECT MAX(indexed_at) FROM files")
            last_indexed = self.cursor.fetchone()[0]
            info['last_indexed'] = last_indexed or "从未索引"
            
            return info
        except:
            return None
        finally:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None