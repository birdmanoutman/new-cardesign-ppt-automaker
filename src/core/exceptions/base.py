class CoreException(Exception):
    """基础异常类"""
    pass

class StorageError(CoreException):
    """存储相关错误"""
    pass

class ProcessorError(CoreException):
    """处理器相关错误"""
    pass 