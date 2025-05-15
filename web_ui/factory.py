from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    # 加载环境变量
    load_dotenv()
    
    app = Flask(__name__)
    # 确保instance目录存在
    instance_path = os.path.join(os.path.dirname(__file__), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    app.config['DATABASE'] = os.path.join(instance_path, 'app.db')
    app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'your-secret-key')
    
    # 配置日志
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        os.makedirs('web_ui/logs', exist_ok=True)
        file_handler = RotatingFileHandler('web_ui/logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
    
    return app
