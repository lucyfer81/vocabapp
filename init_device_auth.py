#!/usr/bin/env python3
"""
数据库初始化脚本 - 添加设备授权表
"""

from database import db
from app import app
from models import DeviceAuth
import datetime

def init_device_auth():
    """初始化设备授权表"""
    with app.app_context():
        # 创建所有表（如果已存在则不会重复创建）
        db.create_all()
        print("数据库表创建/更新完成")
        
        # 检查DeviceAuth表是否已存在数据
        device_count = DeviceAuth.query.count()
        print(f"当前已授权设备数: {device_count}")

if __name__ == '__main__':
    init_device_auth()