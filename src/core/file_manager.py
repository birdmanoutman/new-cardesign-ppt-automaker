import os
import re
from datetime import datetime
import shutil
from pathlib import Path

class FileManager:
    def __init__(self):
        self._init_patterns()
        self._init_cache()
        self._init_config()
        
        # 添加排除重命名的文件夹列表
        self.excluded_folders = {
            'IMG', 'VIDEO', '3D', 'TXT', 'OTHER', 'Photos', 'Share'
        }
    
    def _init_patterns(self):
        """初始化所有正则表达式模式"""
        self.date_patterns = self._create_date_patterns()
        self.patterns = self._create_patterns()
        self.ignore_patterns = self._create_ignore_patterns()
    
    def _init_cache(self):
        """初始化缓存系统"""
        self._file_stats_cache = {}
        self._cache_size = 1000
    
    def _init_config(self):
        """初始化配置参数"""
        self.min_year = 1949
        self.max_year = datetime.now().year
    
    def _create_date_patterns(self) -> dict:
        """创建基础日期模式"""
        return {
            'year': r'([12][90]\d{2})',
            'month': r'(0[1-9]|1[0-2])',
            'day': r'(0[1-9]|[12][0-9]|3[01])',
            'short_month': r'(\d{1,2})',
            'short_day': r'(\d{1,2})',
        }
    
    def _create_patterns(self) -> dict:
        """创建所有正则表达式模式"""
        patterns = {
            'existing_date': re.compile(r'^\d{8}_'),
            'full_date': re.compile(f"{self.date_patterns['year']}{self.date_patterns['month']}{self.date_patterns['day']}"),
            'full_date_with_separators': re.compile(f"{self.date_patterns['year']}[-_]?{self.date_patterns['month']}[-_]?{self.date_patterns['day']}"),
            'full_date_dot': re.compile(r'(\d{4})\.(\d{1,2})\.(\d{1,2})'),
            'full_date_cn': re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日'),
            'cn_year_month': re.compile(r'(\d{4})年(\d{1,2})月'),
            'month_day_cn': re.compile(r'(\d{1,2})月(\d{1,2})日'),
            'year_only': re.compile(r'(?<!\d)([12][90]\d{2})(?!\d)'),
            'year_month_only': re.compile(r'(?<!\d)(20\d{2}(?:0[1-9]|1[0-2]))(?!\d)'),
            'six_digit_date': re.compile(r'(?<!\d)(\d{6})(?!\d)'),
            'space_symbol': re.compile(r'[\s\-]+'),
            'multiple_underscores': re.compile(r'_{2,}'),
            'trailing_symbols': re.compile(r'[\s_\-]+(?=\.\w+$)|[\s_\-]+$'),
            'english_word': re.compile(r'[a-zA-Z]+'),
            'word_boundaries': re.compile(r'[_\s-]+([a-zA-Z])'),
            'first_word': re.compile(r'^[a-zA-Z]'),
            'camel_case': re.compile(r'[A-Z][a-z]+|[A-Z]{2,}(?=[A-Z][a-z]|\d|\W|$)|\d+|[a-z]+'),
            'spaced_date': re.compile(r'(\d{4})\s+(\d{1,2})\s+(\d{1,2})'),  # 匹配空格分隔的日期
            'mixed_date': re.compile(r'(\d{4})[\s\-_.]*(\d{1,2})[\s\-_.]*(\d{1,2})'),  # 匹配混合分隔符的日期
        }
        return patterns
    
    def _create_ignore_patterns(self) -> dict:
        """创建需要忽略的文件模式"""
        return {
            'hidden_files': re.compile(r'^\.|/\.'),
            'system_files': re.compile(r'^(desktop\.ini|thumbs\.db|\.ds_store)$', re.IGNORECASE),
            'temp_files': re.compile(r'(^~\$.*)|~$|\.(tmp|temp|bak|swp)$', re.IGNORECASE),
            'lock_files': re.compile(r'\.lock$|\.lck$', re.IGNORECASE),
        }
    
    def _is_camel_case(self, text: str) -> bool:
        """
        检查文是否已经是驼峰命名格式
        """
        # 检查是否包含至少一个大写字母（不在开头的位置）
        return bool(re.search(r'^[a-z][a-zA-Z0-9]*[A-Z]', text))
    
    def _is_uppercase_word(self, text: str) -> bool:
        """
        检查是否是大写缩写词（全大写且长度大于1）或特殊格式
        """
        # 检查是否全写
        if text.isupper() and len(text) > 1:
            return True
        # 检查是否是特殊格式（如 ConceptCar）
        if re.match(r'^[A-Z][a-z]+[A-Z][a-z]+$', text):
            return True
        return False
    
    def _to_camel_case(self, text: str) -> str:
        """
        将文本转换为驼峰命名格式
        """
        # 检查是否包含英文单词
        if not re.search(r'[a-zA-Z]', text):
            return text
        
        # 将文本按所有可能的分隔符分割（空格、下划线、横杠等）
        words = re.split(r'[_\s\-]+', text)
        result = []
        
        for i, word in enumerate(words):
            if not word:  # 跳过空字符串
                continue
            
            # 处理纯数字
            if word.isdigit():
                result.append(word)
                continue
            
            # 处理混合了数字和字母的情况
            if re.search(r'\d', word):
                # 在数字和字母之间添加分隔
                parts = re.findall(r'[0-9]+|[a-zA-Z]+', word)
                for j, part in enumerate(parts):
                    if part.isdigit():
                        result.append(part)
                    else:
                        if i == 0 and j == 0:  # 第一个词的第一个字母部分
                            result.append(part.lower())
                        else:
                            result.append(part.capitalize())
            else:
                # 纯字母的情况
                if i == 0:  # 第一个词小写
                    result.append(word.lower())
                else:  # 其他词首字母大写
                    result.append(word.capitalize())
        
        return ''.join(result)
    
    def standardize_filename(self, filepath: str, rules: dict, override_date: datetime = None) -> str:
        """
        根据规则标准化单个文件名
        """
        add_default_date = rules.get('add_default_date', True)
        use_camel_case = rules.get('use_camel_case', False)
        name, ext = os.path.splitext(Path(filepath).name)
        
        # 如果已经有标准化的日期前缀，则返回原文件名
        if self.patterns['existing_date'].match(name):
            return Path(filepath).name
        
        # 获取文件时间信息
        creation_date = self._get_creation_date(filepath)
        
        # 提取日期并从文件名中删除日期信息
        date_str, cleaned_name = self._extract_and_remove_date(name, creation_date, add_default_date)
        
        # 如果没有找到日期信息且需要添加默认日期，使用文件创建时间
        if not date_str and add_default_date:
            date_str = creation_date.strftime('%Y%m%d')
        
        # 标准化空格和符号
        normalized_name = re.sub(r'\s+', '_', cleaned_name)  # 替换空格为下划线
        normalized_name = self.patterns['multiple_underscores'].sub('_', normalized_name)
        normalized_name = normalized_name.strip('_')
        
        # 如果启用驼峰命名，处理英文部分
        if use_camel_case:
            # 先按下划线分割
            parts = normalized_name.split('_')
            processed_parts = [self._to_camel_case(part) for part in parts if part]
            normalized_name = ''.join(processed_parts)
        
        # 构建新文件名
        if date_str:
            new_filename = f"{date_str}_{normalized_name}"
            new_filename = new_filename.strip('_')
            final_filename = f"{new_filename}{ext}"
            return final_filename
        
        return f"{normalized_name}{ext}"
    
    def _is_valid_date(self, year: int, month: int, day: int) -> bool:
        """
        验证日期是否在有效范围内
        """
        try:
            # 检查年份范围
            if not (self.min_year <= year <= self.max_year):
                return False
            
            # 验证日期是否有效
            datetime(year, month, day)
            return True
        except ValueError:
            return False
    
    def _is_valid_yymmdd(self, yy: int, mm: int, dd: int) -> bool:
        """
        验证是否是有效的YYMMDD格式日期
        """
        try:
            # 确定世纪
            year = 2000 + yy if yy < 50 else 1900 + yy
            if not (self.min_year <= year <= self.max_year):
                return False
            # 验证日期是否有效
            datetime(year, mm, dd)
            return True
        except ValueError:
            return False
    
    def _is_valid_yyyymm(self, yyyy: int, mm: int) -> bool:
        """
        验证是否是有效的YYYYMM格式日期
        """
        try:
            if not (self.min_year <= yyyy <= self.max_year):
                return False
            # 验证月份是否有效
            if not (1 <= mm <= 12):
                return False
            return True
        except ValueError:
            return False
    
    def _extract_and_remove_date(self, name: str, creation_date: datetime, add_default_date: bool) -> tuple[str, str]:
        """
        从文件名中提取日期并返回清理后的文件名
        返回: (日期字符串, 清理后的文件名)
        """
        current_year = creation_date.year
        cleaned_name = name
        file_dates = [creation_date]
        
        # 存储所有找到的日期信息
        found_dates = []
        
        # 尝试匹配所有可能的日期格式
        # 整日期格式（8位）
        for pattern_name in ['full_date', 'full_date_with_separators']:
            for match in self.patterns[pattern_name].finditer(name):
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    if self._is_valid_date(year, month, day):
                        found_dates.append({
                            'date_str': f"{year:04d}{month:02d}{day:02d}",
                            'pattern': pattern_name,
                            'match': match,
                            'completeness': 3  # 年月日都有，完整度最高
                        })
                except (ValueError, IndexError):
                    continue
        
        # 年月格式（6位）
        for match in self.patterns['year_month_only'].finditer(name):
            year_month = match.group(1)
            year = int(year_month[:4])
            month = int(year_month[4:])
            if self.min_year <= year <= self.max_year:
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}01",
                    'pattern': 'year_month_only',
                    'match': match,
                    'completeness': 2  # 有年月，完整度次之
                })
        
        # 中文年月格式
        for match in self.patterns['cn_year_month'].finditer(name):
            year = int(match.group(1))
            month = int(match.group(2))
            if self.min_year <= year <= self.max_year:
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}01",
                    'pattern': 'cn_year_month',
                    'match': match,
                    'completeness': 2  # 有年月，完整度次之
                })
        
        # 年份格式（4位）
        for match in self.patterns['year_only'].finditer(name):
            year = int(match.group(1))
            if self.min_year <= year <= self.max_year:
                found_dates.append({
                    'date_str': f"{year:04d}0101",
                    'pattern': 'year_only',
                    'match': match,
                    'completeness': 1  # 只有年份，完整度最低
                })
        
        # 尝试匹配独立的6位数字
        for match in self.patterns['six_digit_date'].finditer(name):
            six_digits = match.group(1)
            
            # 尝试解析为YYMMDD格式
            yy = int(six_digits[:2])
            mm_yymmdd = int(six_digits[2:4])
            dd = int(six_digits[4:])
            
            # 尝试解析为YYYYMM格式
            yyyy = int(six_digits[:4])
            mm_yyyymm = int(six_digits[4:])
            
            # 检查哪种格式有效
            is_yymmdd = self._is_valid_yymmdd(yy, mm_yymmdd, dd)
            is_yyyymm = self._is_valid_yyyymm(yyyy, mm_yyyymm)
            
            if is_yymmdd:
                # 是有效的YYMMDD格式
                year = 2000 + yy if yy < 50 else 1900 + yy
                found_dates.append({
                    'date_str': f"{year:04d}{mm_yymmdd:02d}{dd:02d}",
                    'pattern': 'six_digit_yymmdd',
                    'match': match,
                    'completeness': 3  # 年月日都有，完整度最高
                })
            elif is_yyyymm:
                # 是有效的YYYYMM格式
                found_dates.append({
                    'date_str': f"{yyyy:04d}{mm_yyyymm:02d}01",
                    'pattern': 'six_digit_yyyymm',
                    'match': match,
                    'completeness': 2  # 只有年月，完整度次之
                })
        
        # 尝试匹配带点的完整日期（如2021.11.7）
        match = self.patterns['full_date_dot'].search(name)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            if self._is_valid_date(year, month, day):
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}{day:02d}",
                    'pattern': 'full_date_dot',
                    'match': match,
                    'completeness': 3  # 年月日都有，完整度最高
                })
        
        # 尝试匹配完整中文日期（如2022年09月25日）
        match = self.patterns['full_date_cn'].search(name)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            if self._is_valid_date(year, month, day):
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}{day:02d}",
                    'pattern': 'full_date_cn',
                    'match': match,
                    'completeness': 3  # 年月日都有，完整度最高
                })
        
        # 尝试匹配中文年月（如2022年09月）
        match = self.patterns['cn_year_month'].search(name)
        if match and not self.patterns['full_date_cn'].search(name):  # 避免与完整日期重复匹配
            year = int(match.group(1))
            month = int(match.group(2))
            if self._is_valid_date(year, month, 1):
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}01",
                    'pattern': 'cn_year_month',
                    'match': match,
                    'completeness': 2  # 有年月，完整度次之
                })
        
        # 尝试匹配中文月日（如9月25日）
        match = self.patterns['month_day_cn'].search(name)
        if match and not self.patterns['full_date_cn'].search(name):  # 避免与完整日期重复匹配
            month = int(match.group(1))
            day = int(match.group(2))
            if self._is_valid_date(current_year, month, day):
                found_dates.append({
                    'date_str': f"{current_year:04d}{month:02d}{day:02d}",
                    'pattern': 'month_day_cn',
                    'match': match,
                    'completeness': 2  # 有月日，完整度���之
                })
        
        # 添加对空格分隔日期的处理
        match = self.patterns['spaced_date'].search(name)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            if self._is_valid_date(year, month, day):
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}{day:02d}",
                    'pattern': 'spaced_date',
                    'match': match,
                    'completeness': 3  # 年月日都有，完整度最高
                })
        
        # 添加对混合分隔符日期的处理
        match = self.patterns['mixed_date'].search(name)
        if match and not self.patterns['spaced_date'].search(name):  # 避免重复匹配
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            if self._is_valid_date(year, month, day):
                found_dates.append({
                    'date_str': f"{year:04d}{month:02d}{day:02d}",
                    'pattern': 'mixed_date',
                    'match': match,
                    'completeness': 3  # 年月日都有，完整度最高
                })
        
        # 如果找到了日期信息，选择最完整的一个
        if found_dates:
            # 按完整度降序和日期升序排序（相同完整度选择早的日期）
            found_dates.sort(key=lambda x: (x['completeness'], -int(x['date_str'])), reverse=True)
            best_date = found_dates[0]
            
            # 只从文件名中删除被选中的日期信息
            cleaned_name = name.replace(best_date['match'].group(), '')
            
            # 清理多余的分隔符
            cleaned_name = self.patterns['multiple_underscores'].sub('_', cleaned_name)
            cleaned_name = cleaned_name.strip('_- ')
            
            return best_date['date_str'], cleaned_name
        
        # 如果没有找到任何有效的日期格式，返回空字符和原始名称
        return "", name
    
    def should_ignore_file(self, filename: str) -> bool:
        """
        检查文件是否应该被忽略
        """
        # 检查所有忽略模式
        for pattern in self.ignore_patterns.values():
            if pattern.search(filename.lower()):
                return True
        return False
    
    def should_ignore_folder_rename(self, folder_name: str) -> bool:
        """
        检查文件夹是否应该被排除在重命名之外
        """
        return folder_name in self.excluded_folders
    
    def batch_rename(self, directory: str, rules: dict) -> dict:
        """
        批量重命名文件
        """
        results = {}
        rename_folders = rules.get('rename_folders', False)
        
        for filename in os.listdir(directory):
            # 检查是否应该忽略该文件
            if self.should_ignore_file(filename):
                continue
            
            original_path = os.path.join(directory, filename)
            
            # 检查是否为目录
            if os.path.isdir(original_path) and not rename_folders:
                continue
                
            new_filename = self.standardize_filename(original_path, rules)
            if new_filename != filename:
                new_path = os.path.join(directory, new_filename)
                try:
                    if os.path.isdir(original_path):
                        os.rename(original_path, new_path)
                    else:
                        shutil.move(original_path, new_path)
                    results[filename] = {'new_name': new_filename, 'status': 'success'}
                except Exception as e:
                    results[filename] = {'new_name': new_filename, 'status': 'error', 'message': str(e)}
            else:
                results[filename] = {'new_name': filename, 'status': 'skipped'}
                
        return results 
    
    def get_windows_creation_time(self, filepath: str) -> datetime:
        """
        使用 pywin32 获取 Windows 文件的准确创建时间
        """
        try:
            import win32file
            import pywintypes
            
            handle = win32file.CreateFileW(
                filepath,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            
            try:
                creation_time, access_time, write_time = win32file.GetFileTime(handle)
                # pywintypes.datetime 对象可直接转换为 Python datetime
                creation_date = creation_time.astimezone().replace(tzinfo=None)  # 转换为本地时间并移除时区信息
                # print(f"pywin32 原始创建时间: {creation_time}")
                # print(f"pywin32 转换后时间: {creation_date}")
                return creation_date
            finally:
                handle.Close()
                
        except ImportError:
            # print("pywin32 未安装")
            raise
        except Exception as e:
            # print(f"获取 Windows 创建时间出错: {e}")
            raise
    
    def _get_file_stats(self, filepath: str) -> tuple[datetime, datetime]:
        """
        获取文件的创建和修改时间，使用缓存优化性能
        """
        if filepath in self._file_stats_cache:
            return self._file_stats_cache[filepath]
            
        try:
            if os.name == 'nt':
                # Windows系统使用 win32file
                import win32file
                handle = win32file.CreateFileW(
                    filepath,
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_READ,
                    None,
                    win32file.OPEN_EXISTING,
                    win32file.FILE_ATTRIBUTE_NORMAL,
                    None
                )
                try:
                    creation_time, _, write_time = win32file.GetFileTime(handle)
                    creation_date = creation_time.astimezone().replace(tzinfo=None)
                    write_date = write_time.astimezone().replace(tzinfo=None)
                finally:
                    handle.Close()
            else:
                # Unix系统
                stat = os.stat(filepath)
                creation_date = datetime.fromtimestamp(stat.st_ctime)
                write_date = datetime.fromtimestamp(stat.st_mtime)
            
            # 缓存结果
            result = (creation_date, write_date)
            if len(self._file_stats_cache) >= self._cache_size:
                # 如果缓存已，删除最早条目
                self._file_stats_cache.pop(next(iter(self._file_stats_cache)))
            self._file_stats_cache[filepath] = result
            return result
            
        except Exception:
            # 出错时返回修改时间
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            return (mtime, mtime)
    
    def _get_creation_date(self, filepath):
        """获取文件的创建日期"""
        import os
        import platform
        from datetime import datetime
        
        if platform.system() == 'Windows':
            return datetime.fromtimestamp(os.path.getctime(filepath))
        else:
            stat = os.stat(filepath)
            try:
                return datetime.fromtimestamp(stat.st_birthtime)  # Mac OS
            except AttributeError:
                return datetime.fromtimestamp(stat.st_mtime)  # Linux