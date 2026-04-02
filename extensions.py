"""
Flask 扩展初始化
所有扩展在此统一创建，避免循环导入。
"""
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
