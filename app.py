import os
import logging
from functools import wraps
from dotenv import load_dotenv
from backend.functions.utils import find_calendar_date
from flask import Flask, send_from_directory, jsonify, request, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restful import Api
from flask_admin import Admin
from backend.celery.celery_app import init_celery
from backend.models.models import db_setup
from backend.school.models import register_commands
from backend.functions.utils import refreshdatas
from flask_socketio import SocketIO, join_room, leave_room, emit
import asyncio
from backend.telegram_bot.views import register_telegram_bot_routes
import os
from dotenv import load_dotenv
from backend.tasks.missions.utils import recurring_check
import time
from flask import send_from_directory
import os
import redis

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_PREFIX = 'api/'
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'rimefara')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'top12')
GITHUB_SECRET = os.getenv('GITHUB_SECRET', '').encode()

classroom_server = os.getenv("CLASSROOM_SERVER_URL")
school_server = os.getenv("SCHOOL_SERVER_URL")
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0
)
# ⭐ Initialize socketio OUTSIDE the function as a global variable
socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent', logger=True, engineio_logger=True,
                    ping_timeout=60,
                    ping_interval=25)




def create_app(config_name='backend.models.config'):
    """Application factory pattern for better testing and configuration"""

    app = Flask(
        __name__,
        static_folder="frontend/build",
        static_url_path="/"
    )

    # Configuration
    app.config.from_object(config_name)

    # Define media folder path
    MEDIA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')
    app.config['MEDIA_FOLDER'] = MEDIA_FOLDER

    # CORS - more specific configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv('ALLOWED_ORIGINS', '*').split(','),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"]
        },
        r"/media/*": {
            "origins": os.getenv('ALLOWED_ORIGINS', '*').split(','),
            "methods": ["GET"],
            "allow_headers": ["Content-Type"]
        }
    })

    # ⭐ Initialize socketio with the app (bind it to the Flask app)
    socketio.init_app(
        app,
        message_queue='redis://localhost:6379/0',  # ✅ Add this!
        cors_allowed_origins="*"
    )

    # Initialize extensions
    db = db_setup(app)
    migrate = Migrate(app, db)
    jwt = JWTManager(app)
    api = Api(app)

    # Flask-Admin
    admin = Admin(
        app,
        name='Gennis',
        template_mode='bootstrap3',
        static_url_path='/flask_static'
    )

    # Register CLI commands
    register_commands(app)

    # Register all blueprints and routes
    register_all_routes(api, app)

    # Register error handlers
    register_error_handlers(app)

    # Register middleware
    register_middleware(app)

    # ⭐ Register SocketIO event handlers
    register_socketio_handlers()

    init_celery(app)

    return app


def register_socketio_handlers():
    """Register SocketIO event handlers"""

    @socketio.on('connect')
    def handle_connect():
        logger.info(f'✅ Client connected: {request.sid}')
        emit('connection_response', {'status': 'connected', 'sid': request.sid})

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f'❌ Client disconnected: {request.sid}')

    @socketio.on('join')
    def handle_join(data):
        """Client joins their user-specific room"""
        user_id = data.get('user_id')
        if user_id:
            room = f'user_{user_id}'
            join_room(room)
            logger.info(f'👤 User {user_id} joined room: {room}')
            emit('join_response', {'status': 'joined', 'room': room, 'user_id': user_id})

    @socketio.on('leave')
    def handle_leave(data):
        """Client leaves their room"""
        user_id = data.get('user_id')
        if user_id:
            room = f'user_{user_id}'
            leave_room(room)
            logger.info(f'👋 User {user_id} left room: {room}')

    @socketio.on('test_emit')
    def handle_test():
        """Test emission endpoint"""
        emit('test_response', {'message': 'Test successful!', 'timestamp': time.time()})
        logger.info('🧪 Test emit received and responded')


def register_all_routes(api, app):
    """Centralized route registration"""

    # Import all view registration functions
    from backend.time_table.views import register_time_table_views
    from backend.student.views import register_student_views
    from backend.teacher.views import register_teacher_views
    from backend.group.views import register_group_views
    from backend.lead.views import register_lead_views
    from backend.home_page.views import register_home_views
    from backend.account.views import register_account_views
    from backend.book.views import register_book_views
    from backend.student.register_for_tes.views import register_for_tes_views
    from backend.school.views import register_school_views
    from backend.routes.views import register_router_views
    from backend.mobile.views import register_parent_mobile_views
    from backend.for_programmers.views import register_programmers_views
    from backend.account.overall_datas.views import register_overall_datas_routes
    from backend.parent.views import register_parent_views
    from backend.tasks.admin.views import register_task_rating_views
    from backend.telegram_bot.views import register_telegram_bot_routes
    from backend.tasks.missions.views import register_missions_views

    # Register all routes
    routes = [
        register_time_table_views,
        register_router_views,
        register_parent_views,
        register_task_rating_views,
        register_student_views,
        register_telegram_bot_routes,
        register_teacher_views,
        register_group_views,
        register_lead_views,
        register_home_views,
        register_account_views,
        register_book_views,
        register_for_tes_views,
        register_school_views,
        register_parent_mobile_views,
        register_programmers_views,
        register_overall_datas_routes,
        register_missions_views
    ]

    for register_func in routes:
        try:
            register_func(api, app)
        except Exception as e:
            logger.error(f"Failed to register {register_func.__name__}: {e}")


def register_error_handlers(app):
    """Centralized error handling"""

    @app.errorhandler(404)
    def not_found(e):
        """Serve React app for client-side routing"""
        if request.path.startswith('/api/'):
            return jsonify({
                "success": False,
                "msg": "API endpoint not found"
            }), 404
        return app.send_static_file('index.html')

    @app.errorhandler(413)
    def request_entity_too_large(e):
        """Handle file upload size exceeded"""
        return jsonify({
            "success": False,
            "msg": "Fayl hajmi juda katta"
        }), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle internal server errors"""
        logger.error(f"Internal server error: {e}")
        return jsonify({
            "success": False,
            "msg": "Ichki server xatosi"
        }), 500

    @app.errorhandler(401)
    def unauthorized(e):
        """Handle unauthorized access"""
        return jsonify({
            "success": False,
            "msg": "Ruxsat berilmagan"
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        """Handle forbidden access"""
        return jsonify({
            "success": False,
            "msg": "Taqiqlangan"
        }), 403

    # In app.py or your routes
    @app.route('/test-call-status/<int:user_id>/')
    def test_call_status(user_id):
        """Test call status emission"""
        from app import socketio

        test_data = {
            'student_id': "99999",
            'status': 'validating',
            'message': 'TEST: Validating call parameters...',
            'timestamp': time.time()
        }

        logger.info(f"📡 Test emitting to user_{user_id}: {test_data}")
        socketio.emit('call_status', test_data, room=f'user_{user_id}')

        return jsonify({
            'message': f'Emitted test to user_{user_id}',
            'data': test_data
        })


def register_middleware(app):
    """Register application middleware"""

    @app.before_request
    def require_auth_for_admin():
        """Protect admin routes with basic auth"""
        if request.path.startswith('/admin'):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()

    @app.before_request
    def log_request():
        """Log incoming requests (optional, can be disabled in production)"""
        if app.config.get('LOG_REQUESTS', False):
            logger.info(f"{request.method} {request.path}")

    @app.before_request
    def auto_recurring_run():
        recurring_check()


def check_auth(username, password):
    """Verify username and password"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def authenticate():
    """Send 401 response for authentication"""
    return Response(
        'Unauthorized access. Please provide valid credentials.',
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


# Create app instance
app = create_app()


@app.route('/', methods=['GET', 'POST'])
def index():
    """Serve React application"""
    if request.method == 'POST':
        try:
            calendar_year, calendar_month, calendar_day = find_calendar_date()
        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")

    return app.send_static_file("index.html")


@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files (audio recordings, etc.)"""
    return send_from_directory(app.config['MEDIA_FOLDER'], filename)


@app.route('/flask_static/<path:filename>')
def flask_admin_static(filename):
    """Serve Flask-Admin static files"""
    return send_from_directory('static', filename)


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "service": "gennis-backend"
    }), 200


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
