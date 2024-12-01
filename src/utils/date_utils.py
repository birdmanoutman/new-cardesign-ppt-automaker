from datetime import datetime
import os

class DateUtils:
    @staticmethod
    def is_valid_date(year: int, month: int, day: int, min_year: int, max_year: int) -> bool:
        """验证日期是否在有效范围内"""
        try:
            if not (min_year <= year <= max_year):
                return False
            datetime(year, month, day)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_yymmdd(yy: int, mm: int, dd: int, min_year: int, max_year: int) -> bool:
        """验证是否是有效的YYMMDD格式日期"""
        try:
            year = 2000 + yy if yy < 50 else 1900 + yy
            if not (min_year <= year <= max_year):
                return False
            datetime(year, mm, dd)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_file_dates(filepath: str) -> tuple[datetime, datetime]:
        """获取文件的创建和修改时间"""
        try:
            if os.name == 'nt':
                return DateUtils._get_windows_file_dates(filepath)
            return DateUtils._get_unix_file_dates(filepath)
        except Exception:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            return mtime, mtime 