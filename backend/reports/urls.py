from backend.reports.views import report_bp


def register_report_views(api, app):
    app.register_blueprint(report_bp, url_prefix=f"/api/reports")