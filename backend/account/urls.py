from backend.account.account import account_bp


def register_account_views(api, app):
    app.register_blueprint(account_bp, url_prefix=f"/{api}/account")
    # app.register_blueprint(get_parent_bp, url_prefix=f"/{api}/parent")
