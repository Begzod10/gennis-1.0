from backend.account.account import account_bp
from backend.account.debit_credit.views import account_debit_credit
from backend.account.overhead_capital import account_capital_bp
from backend.account.payment import account_payment_bp
from backend.account.profile.camp_staff import account_camp_staff
from backend.account.profile.divident_views import account_dividend_bp
from backend.account.profile.encashment import account_encashment_bp
from backend.account.profile.investment import account_investment
from backend.account.profile.overhead import account_overhead_bp
from backend.account.profile.payable_views import account_payable
from backend.account.salary import account_salary_bp
from backend.account.test_acc import account_test_bp


def register_account_views(api, app):
    app.register_blueprint(account_debit_credit, url_prefix=f"/{api}/account")
    app.register_blueprint(account_camp_staff, url_prefix=f"/{api}/account")
    app.register_blueprint(account_dividend_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_encashment_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_investment, url_prefix=f"/{api}/account")
    app.register_blueprint(account_overhead_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_payable, url_prefix=f"/{api}/account")
    app.register_blueprint(account_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_capital_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_payment_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_test_bp, url_prefix=f"/{api}/account")
    app.register_blueprint(account_salary_bp, url_prefix=f"/{api}/account")
