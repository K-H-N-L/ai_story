#!/usr/bin/env python
"""Django项目管理脚本"""
import os
import sys
from pathlib import Path


def load_env():
    """从项目根目录加载 .env 文件"""
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"✓ 已加载环境变量: {env_path}")


def main():
    """运行管理任务"""
    load_env()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
