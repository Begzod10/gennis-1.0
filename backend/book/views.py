from backend.book.book_acc import book_acc_bp
from backend.book.book_orm import book_orm_bp


def register_book_views(api, app):
    app.register_blueprint(book_acc_bp, url_prefix=f"/{api}/book")
    app.register_blueprint(book_orm_bp, url_prefix=f"/{api}/book")
