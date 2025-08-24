#!/usr/bin/env python3
"""
数据库迁移脚本：为DeviceAuth表添加设备指纹唯一约束
"""
import sqlite3
import os
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """执行数据库迁移"""
    db_path = 'wordbook.db'
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件 {db_path} 不存在")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查DeviceAuth表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='DeviceAuth'
        """)
        
        if not cursor.fetchone():
            logger.warning("DeviceAuth表不存在，无需迁移")
            return True
        
        # 检查是否已经存在唯一约束
        cursor.execute("PRAGMA index_list(DeviceAuth)")
        indexes = cursor.fetchall()
        
        unique_constraint_exists = False
        for index in indexes:
            if index[1].startswith('sqlite_autoindex_DeviceAuth'):
                # 检查是否是设备指纹的唯一索引
                cursor.execute(f"PRAGMA index_info({index[1]})")
                index_info = cursor.fetchall()
                for info in index_info:
                    if info[2] == 'device_fingerprint':
                        unique_constraint_exists = True
                        break
        
        if unique_constraint_exists:
            logger.info("设备指纹唯一约束已存在，无需迁移")
            return True
        
        # 查找重复的设备指纹
        cursor.execute("""
            SELECT device_fingerprint, COUNT(*) as count 
            FROM DeviceAuth 
            GROUP BY device_fingerprint 
            HAVING count > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.warning(f"发现 {len(duplicates)} 个重复的设备指纹")
            
            # 处理重复的设备指纹：禁用旧的记录，保留最新的
            for fingerprint, count in duplicates:
                logger.info(f"处理重复设备指纹: {fingerprint[:16]}... ({count} 条记录)")
                
                # 找到该指纹的所有记录，按创建时间排序
                cursor.execute("""
                    SELECT id, user_id, created_at, is_active 
                    FROM DeviceAuth 
                    WHERE device_fingerprint = ? 
                    ORDER BY created_at DESC
                """, (fingerprint,))
                
                records = cursor.fetchall()
                
                # 保留最新的记录，禁用其他的
                if len(records) > 1:
                    keep_record = records[0]  # 保留最新的
                    disable_records = records[1:]  # 禁用其他的
                    
                    for record in disable_records:
                        cursor.execute("""
                            UPDATE DeviceAuth 
                            SET is_active = 0 
                            WHERE id = ?
                        """, (record[0],))
                        logger.info(f"  - 禁用记录 {record[0]} (用户 {record[1]})")
                    
                    logger.info(f"  - 保留记录 {keep_record[0]} (用户 {keep_record[1]})")
        
        # 创建新的表结构
        cursor.execute("""
            CREATE TABLE DeviceAuth_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_fingerprint VARCHAR(255) NOT NULL UNIQUE,
                device_name VARCHAR(100),
                auth_token VARCHAR(255) NOT NULL UNIQUE,
                created_at VARCHAR(50) NOT NULL,
                last_used VARCHAR(50),
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES User (id) ON DELETE CASCADE,
                UNIQUE(user_id, device_fingerprint)
            )
        """)
        
        # 复制数据
        cursor.execute("""
            INSERT INTO DeviceAuth_new (id, user_id, device_fingerprint, device_name, auth_token, created_at, last_used, is_active)
            SELECT id, user_id, device_fingerprint, device_name, auth_token, created_at, last_used, is_active
            FROM DeviceAuth
            WHERE is_active = 1
        """)
        
        # 删除旧表
        cursor.execute("DROP TABLE DeviceAuth")
        
        # 重命名新表
        cursor.execute("ALTER TABLE DeviceAuth_new RENAME TO DeviceAuth")
        
        # 提交更改
        conn.commit()
        
        logger.info("数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if migrate_database():
        logger.info("迁移成功")
        sys.exit(0)
    else:
        logger.error("迁移失败")
        sys.exit(1)