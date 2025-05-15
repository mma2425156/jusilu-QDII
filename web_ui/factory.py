from flask import Flask
import os

def create_app(test_config=None):
    """创建并配置Flask应用"""
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_ui', 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_ui', 'static'))
    
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'qdii.sqlite'),
        MAIL_CONFIG_PATH=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'mail_config.json'),
    )

    # 确保instance文件夹存在
    try:
        os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance'))
    except OSError:
        pass
        
    # 确保config文件夹存在
    try:
        os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config'))
    except OSError:
        pass

    return app
