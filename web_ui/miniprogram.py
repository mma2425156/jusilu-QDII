from flask import Blueprint, request, jsonify
import jwt
import datetime
from functools import wraps

def create_miniprogram_blueprint():
    """创建小程序蓝图工厂函数"""
    miniprogram = Blueprint('miniprogram', __name__, url_prefix='/api/miniprogram')
    
    # 配置JWT
    from web_ui.factory import create_app
    app = create_app()

    # 配置JWT
    app.config['JWT_SECRET'] = 'your-secret-key'  # 生产环境应从环境变量获取
    app.config['JWT_EXPIRE'] = datetime.timedelta(hours=24)

    def token_required(f):
        """JWT认证装饰器"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'status': 'error', 'message': 'Token缺失'}), 401
                
            try:
                data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            except Exception as e:
                return jsonify({'status': 'error', 'message': 'Token无效'}), 401
                
            return f(*args, **kwargs)
        return decorated

    @miniprogram.route('/login', methods=['POST'])
    def login():
        """小程序登录接口"""
        data = request.get_json()
        # 这里应接入微信官方登录API验证code
        # 示例代码，实际应调用微信接口
        if data.get('code'):
            # 模拟生成用户ID
            user_id = 'wx_' + data['code'][-8:]
            
            # 生成JWT
            token = jwt.encode({
                'user_id': user_id,
                'exp': datetime.datetime.utcnow() + app.config['JWT_EXPIRE']
            }, app.config['JWT_SECRET'])
            
            return jsonify({
                'status': 'success',
                'token': token,
                'user_info': {
                    'user_id': user_id,
                    'nickname': '微信用户'
                }
            })
        return jsonify({'status': 'error', 'message': 'code缺失'}), 400

    @miniprogram.route('/qdii_data', methods=['GET'])
    @token_required
    def get_qdii_data():
        """获取QDII数据接口"""
        try:
            # 这里应集成现有数据获取逻辑
            # 示例返回结构
            return jsonify({
                'status': 'success',
                'data': {
                    'update_time': '2023-11-15 10:00:00',
                    'funds': [
                        {
                            'name': '某QDII基金',
                            'premium_rate': 0.05,
                            'status': '开放申购'
                        }
                    ]
                }
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @miniprogram.route('/subscribe', methods=['POST'])
    @token_required
    def subscribe():
        """订阅邮件通知"""
        data = request.get_json()
        # 这里应集成邮件订阅逻辑
        return jsonify({
            'status': 'success',
            'message': '订阅成功'
        })
    
    return miniprogram
