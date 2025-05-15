import sqlite3
import os
from web_ui.factory import create_app

def inspect_db(db_path):
    """检查数据库表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n数据库表结构：")
    for table in tables:
        table_name = table[0]
        print(f"\n表名: {table_name}")
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        print("字段结构：")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - 默认值: {col[4]}")
    
    conn.close()

def test_db_integrity(db_path):
    """测试数据库完整性"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db_path = app.config['DATABASE']
        print("数据库路径:", db_path)
        
        # 检查表结构
        inspect_db(db_path)
        
        # 测试完整性
        print("\n数据库完整性检查:", test_db_integrity(db_path))
