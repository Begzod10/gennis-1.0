from .routes import chat_analyzer_bp


def register_chat_analyzer_routes(api, app):
    app.register_blueprint(chat_analyzer_bp, url_prefix="/api/chat-analyzer")
