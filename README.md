# PPT 自动生成工具

## 项目简介
这是一个用于自动生成汽车设计PPT的工具，可以批量处理图片并自动生成规范化的PPT文档。该工具使用Python开发，提供了友好的图形用户界面。

## 主要功能
- 批量导入和处理图片文件
- 自动生成标准化PPT模板
- 支持多种图片布局方式
- 自动调整图片大小和位置
- 可自定义PPT模板样式
- 支持批量导出PPT文件

## 系统要求
- Python 3.7+
- 依赖库：
  - PyQt5
  - python-pptx
  - Pillow
  - pathlib

## 安装说明
1. 克隆项目到本地

```bash
git clone [项目地址]
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用说明
1. 运行主程序

```bash
python main.py
```

2. 使用步骤
   - 点击"选择文件"按钮导入图片
   - 选择需要的PPT模板样式
   - 设置输出路径
   - 点击"生成PPT"按钮开始处理

## 项目结构
```
project/
├── main.py              # 程序入口
├── src/
│   ├── core/           # 核心处理模块
│   │   ├── file_manager.py    # 文件管理
│   │   └── ppt_processor.py   # PPT处理
│   └── ui/             # 用户界面
│       ├── main_window.py     # 主窗口
│       └── tabs/            # 标签页组件
├── resources/          # 资源文件
└── README.md
```

## 注意事项
- 支持的图片格式：JPG、PNG、TIFF
- 建议使用1920x1080分辨率的图片以获得最佳效果
- 处理大量图片时可能需要等待较长时间

## 贡献指南
欢迎提交Issue和Pull Request来帮助改进项目。

## 许可证
本项目采用 MIT 许可证