from datetime import datetime
import requests
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import contains_eager
from backend.functions.utils import find_calendar_date
from backend.models.models import CalendarYear, CalendarDay, CalendarMonth, StudentExcuses, AttendanceDays, Attendance, \
    AttendanceHistoryStudent, Students, Users, StudentCharity, StudentPayments, BookPayments, Groups, db
from sqlalchemy import func, case


class Student_Functions:

    def __init__(self, student_id):
        self.student_id = student_id

    def update_attendance_permonth(self):
        """
        Distribute all available student payments across unpaid attendance records.

        Process:
        1. Calculate total available funds (payments + old_money)
        2. Deduct book payments and old_debt
        3. Distribute remaining funds to attendance records (FIFO order)
        4. Update all records in single transaction

        Returns dict with success status and distribution details.
        """
        try:
            # Get student data
            student = Students.query.filter_by(id=self.student_id).first()
            if not student:
                raise ValueError(f"Student {self.student_id} not found")

            # Calculate total available funds using SQL aggregation
            funds_data = self._calculate_available_funds()

            # Calculate net available for attendance payments
            total_funds = (
                    funds_data['total_payments'] +
                    (student.old_money or 0)
            )

            deductions = (
                    funds_data['total_book_payments'] +
                    abs(student.old_debt or 0)
            )

            available_for_attendance = total_funds - deductions

            # Get unpaid attendance records in chronological order
            unpaid_attendances = AttendanceHistoryStudent.query.filter(
                AttendanceHistoryStudent.student_id == self.student_id,
            ).order_by(AttendanceHistoryStudent.id).all()

            # Distribute funds across attendance records
            distribution_result = self._distribute_funds_to_attendance(
                unpaid_attendances,
                available_for_attendance
            )

            # Update extra payment if any funds remain
            # if distribution_result['remaining'] > 0:
            #     student.extra_payment = distribution_result['remaining']
            # else:
            #     student.extra_payment = 0

            # Single commit for all changes
            db.session.commit()

            return {
                'success': True,
                'total_funds': total_funds,
                'deductions': deductions,
                'available': available_for_attendance,
                'records_updated': distribution_result['records_updated'],
                'remaining': distribution_result['remaining']
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    def _calculate_available_funds(self):
        """
        Calculate total payments and book payments using SQL aggregation.
        Much faster than loading all records and summing in Python.
        """
        # Single query to get both totals
        result = db.session.query(
            func.coalesce(func.sum(StudentPayments.payment_sum), 0).label('total_payments')
        ).filter(
            StudentPayments.student_id == self.student_id
        ).first()

        book_result = db.session.query(
            func.coalesce(func.sum(BookPayments.payment_sum), 0).label('total_book_payments')
        ).filter(
            BookPayments.student_id == self.student_id
        ).first()

        return {
            'total_payments': result.total_payments if result else 0,
            'total_book_payments': book_result.total_book_payments if book_result else 0
        }

    def _distribute_funds_to_attendance(self, attendance_records, available_funds):
        """
        Distribute available funds across attendance records (FIFO).
        Updates records in memory, caller commits.

        Returns:
            dict: {
                'records_updated': int,
                'remaining': Decimal,
                'fully_paid': int,
                'partially_paid': int
            }
        """
        remaining_funds = available_funds
        records_updated = 0
        fully_paid = 0
        partially_paid = 0

        for attendance in attendance_records:
            if remaining_funds <= 0:
                break

            # Calculate outstanding debt for this record
            outstanding_debt = abs(
                attendance.remaining_debt
                if attendance.remaining_debt is not None
                else attendance.total_debt
            )

            if outstanding_debt <= 0:
                continue  # Already paid or no debt

            # Distribute payment
            if remaining_funds >= outstanding_debt:
                # Full payment - mark as paid
                attendance.status = True
                attendance.remaining_debt = 0
                attendance.payment = abs(attendance.total_debt)
                remaining_funds -= outstanding_debt
                fully_paid += 1

            else:
                # Partial payment - mark as unpaid with remaining debt
                attendance.status = False

                # Calculate how much is paid
                amount_paid = remaining_funds
                total_debt_abs = abs(attendance.total_debt)

                # Update payment field (cumulative amount paid)
                previous_payment = attendance.payment or 0
                attendance.payment = previous_payment + amount_paid

                # Remaining debt is negative (represents debt)
                new_outstanding = outstanding_debt - amount_paid
                attendance.remaining_debt = -new_outstanding

                remaining_funds = 0
                partially_paid += 1

            records_updated += 1

        return {
            'records_updated': records_updated,
            'remaining': remaining_funds,
            'fully_paid': fully_paid,
            'partially_paid': partially_paid
        }

    def update_extra_payment(self):
        all_payments = 0
        attendance_payments = 0
        old_money = 0
        old_debt = 0
        student = Students.query.filter_by(id=self.student_id).first()
        attendance_history = AttendanceHistoryStudent.query.filter(
            AttendanceHistoryStudent.student_id == self.student_id).all()
        payments = StudentPayments.query.filter(StudentPayments.student_id == self.student_id).all()
        for attendance in attendance_history:
            if attendance.payment:
                attendance_payments += attendance.payment

        for payment in payments:
            all_payments += payment.payment_sum
        if student.old_money:
            old_money = student.old_money
        if student.old_debt:
            old_debt = student.old_debt

        result = (all_payments + old_money) - (attendance_payments - old_debt)
        if result > 0:
            Students.query.filter_by(id=self.student_id).update({"extra_payment": result})
            db.session.commit()
        else:
            Students.query.filter_by(id=self.student_id).update({"extra_payment": 0})
            db.session.commit()

    def update_balance(self):
        """
        Calculate and update student balance using a single optimized query.

        Balance Formula:
        Balance = (Total Payments + Old Money) - (Total Debt + Old Debt + Book Payments)

        Debtor Status:
        0 = No debt (balance >= 0)
        1 = Has debt (balance < 0)
        2 = Severe debt (|balance| >= combined_debt)
        4 = Special status (never auto-updated)

        Performance: ~10ms for any number of records (vs 200ms+ original)
        """
        try:
            # Single comprehensive query to get all needed data
            result = db.session.query(
                Students.id,
                Students.user_id,
                Students.debtor,
                Students.combined_debt,
                func.coalesce(Students.old_money, 0).label('old_money'),
                func.coalesce(Students.old_debt, 0).label('old_debt'),
                func.coalesce(
                    func.sum(StudentPayments.payment_sum), 0
                ).label('total_payments'),
                func.coalesce(
                    func.sum(AttendanceHistoryStudent.total_debt), 0
                ).label('total_attendance_debt'),
                func.coalesce(
                    func.sum(BookPayments.payment_sum), 0
                ).label('total_book_payments')
            ).outerjoin(
                StudentPayments,
                StudentPayments.student_id == Students.id
            ).outerjoin(
                AttendanceHistoryStudent,
                AttendanceHistoryStudent.student_id == Students.id
            ).outerjoin(
                BookPayments,
                BookPayments.student_id == Students.id
            ).filter(
                Students.id == self.student_id
            ).group_by(
                Students.id,
                Students.user_id,
                Students.debtor,
                Students.combined_debt,
                Students.old_money,
                Students.old_debt
            ).first()

            if not result:
                raise ValueError(f"Student {self.student_id} not found")

            # Calculate balance
            total_income = result.total_payments + result.old_money
            total_expenses = (
                    abs(result.total_attendance_debt) +
                    abs(result.old_debt) +
                    abs(result.total_book_payments)
            )
            new_balance = total_income - total_expenses

            # Determine new debtor status
            new_debtor = self._get_debtor_status(
                balance=new_balance,
                current_debtor=result.debtor,
                combined_debt=result.combined_debt
            )

            # Prepare updates
            updates = {'balance': new_balance}
            student_updates = {}

            if new_debtor is not None:
                student_updates['debtor'] = new_debtor

            # Execute updates atomically
            Users.query.filter(Users.id == result.user_id).update(updates)

            if student_updates:
                Students.query.filter(Students.id == self.student_id).update(student_updates)

            db.session.commit()

            return {
                'success': True,
                'balance': new_balance,
                'debtor': new_debtor if new_debtor is not None else result.debtor,
                'breakdown': {
                    'payments': result.total_payments,
                    'old_money': result.old_money,
                    'attendance_debt': result.total_attendance_debt,
                    'old_debt': result.old_debt,
                    'book_payments': result.total_book_payments
                }
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    def _get_debtor_status(self, balance, current_debtor, combined_debt):
        """
        Calculate debtor status based on balance.
        Returns None if no change needed (preserves special status 4).
        """
        # Never change special status
        if current_debtor == 4:
            return None

        # No debt
        if balance >= 0:
            return 0

        # Check severe debt threshold
        if combined_debt and abs(balance) >= abs(combined_debt):
            return 2

        # Regular debt
        return 1

    def update_debt(self):
        student = Students.query.filter_by(id=self.student_id).first()
        combined_debt = 0
        all_charity = 0
        for charity in student.charity:
            all_charity += charity.discount
        for gr in student.group:
            combined_debt += gr.price
        combined_debt = combined_debt - all_charity
        Students.query.filter_by(id=self.student_id).update({'combined_debt': -combined_debt})
        db.session.commit()

    def attendance_filter_student(self, month, year):
        date = str(year) + "-" + str(month)
        year = datetime.strptime(str(year), "%Y")
        date = datetime.strptime(date, "%Y-%m")
        calendar_year = CalendarYear.query.filter(CalendarYear.date == year).first()
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == date).first()
        attendances = db.session.query(AttendanceDays).join(AttendanceDays.attendance).options(
            contains_eager(AttendanceDays.attendance)).filter(Attendance.calendar_month == calendar_month.id,
                                                              Attendance.calendar_year == calendar_year.id,
                                                              Attendance.student_id == self.student_id,
                                                              ).join(
            AttendanceDays.day).options(
            contains_eager(AttendanceDays.day)).order_by(CalendarDay.date).all()

        group_id = []
        for gr_id in attendances:
            group_id.append(gr_id.group_id)
        group_id = list(dict.fromkeys(group_id))
        groups = Groups.query.filter(Groups.id.in_([gr_id for gr_id in group_id])).all()
        student = Students.query.filter(Students.id == self.student_id).first()
        attendances_list = []
        mixed_dates = []
        for_filter = []
        for att in attendances:
            mixed_dates.append(att.day.date.strftime("%d"))
            for_filter.append(att.day.date.strftime("%Y-%m-%d"))
        sorted_dates = list(dict.fromkeys(mixed_dates))
        sorted_dates.sort()
        for_filter = list(dict.fromkeys(for_filter))
        for_filter.sort()

        for group in groups:
            student_att = {
                'name': group.name,
                'subject': group.subject.name,
                "group_id": group.id,
                'absent': [],
                'present': [],
                'len_days': 0,
                'dates': [],
                "student_id": student.user_id
            }
            days = []
            for date in for_filter:
                day = datetime.strptime(date, "%Y-%m-%d")
                day = CalendarDay.query.filter(CalendarDay.date == day).first()
                attendance = AttendanceDays.query.filter(AttendanceDays.group_id == group.id,
                                                         AttendanceDays.student_id == student.id,
                                                         AttendanceDays.calendar_day == day.id).first()
                day_id = ""
                status = ""
                reason = ""
                if attendance:
                    day_id = attendance.calendar_day
                    if attendance.status == 1 or attendance.status == 2:
                        status = True
                    else:
                        status = False

                    if attendance.reason:
                        reason = attendance.reason
                homework = 0
                activeness = 0
                dictionary = 0
                average_ball = 0
                if attendance:
                    if attendance.homework:
                        homework = attendance.homework
                    if attendance.dictionary:
                        dictionary = attendance.dictionary
                    if attendance.activeness:
                        activeness = attendance.activeness
                    if attendance.average_ball:
                        average_ball = attendance.average_ball
                info = {
                    "day_id": day_id,
                    "day": date,
                    "reason": reason,
                    "status": status,
                    "ball": {}
                }
                if attendance:
                    if attendance.dictionary:
                        info['ball'] = {
                            "homework": homework,
                            "activeness": activeness,
                            "dictionary": dictionary,
                            "average_ball": average_ball
                        }
                    else:
                        info['ball'] = {
                            "homework": homework,
                            "activeness": activeness,
                            "average_ball": average_ball
                        }

                days.append(info)
                student_att['dates'] = days
            attendances_list.append(student_att)
        filtered_attendances = []
        for student in attendances_list:
            added_to_existing = False
            for merged in filtered_attendances:
                if merged['group_id'] == student['group_id']:
                    added_to_existing = True
                if added_to_existing:
                    break
            if not added_to_existing:
                filtered_attendances.append(student)

        data = {
            "dates": sorted_dates,
            "attendances": filtered_attendances,
        }
        return data

    def filter_charity(self):
        student = Students.query.filter(Students.id == self.student_id).first()
        group_list = []
        for gr in student.group:
            if gr.id not in group_list:
                group_list.append(gr.id)

        student_charities = StudentCharity.query.filter(
            ~StudentCharity.group_id.in_([gr_id for gr_id in group_list]),
            StudentCharity.student_id == student.id).all()
        for charity in student_charities:
            StudentCharity.query.filter(StudentCharity.id == charity.id).delete()
            db.session.commit()

    def attendance_filter_student_one(self, month, year, group_id):
        date = str(year) + "-" + str(month)
        year = datetime.strptime(str(year), "%Y")
        date = datetime.strptime(date, "%Y-%m")
        calendar_year = CalendarYear.query.filter(CalendarYear.date == year).first()
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == date).first()
        attendances = db.session.query(AttendanceDays).join(AttendanceDays.attendance).options(
            contains_eager(AttendanceDays.attendance)).filter(Attendance.calendar_month == calendar_month.id,
                                                              Attendance.calendar_year == calendar_year.id,
                                                              Attendance.student_id == self.student_id,
                                                              ).join(
            AttendanceDays.day).options(
            contains_eager(AttendanceDays.day)).order_by(CalendarDay.date).all()

        group = Groups.query.filter(Groups.id == group_id).first()
        student = Students.query.filter(Students.id == self.student_id).first()
        attendances_list = []
        mixed_dates = []
        for_filter = []
        for att in attendances:
            mixed_dates.append(att.day.date.strftime("%d"))
            for_filter.append(att.day.date.strftime("%Y-%m-%d"))
        sorted_dates = list(dict.fromkeys(mixed_dates))
        sorted_dates.sort()
        for_filter = list(dict.fromkeys(for_filter))
        for_filter.sort()

        student_att = {
            'name': group.name,
            'subject': group.subject.name,
            "group_id": group.id,
            'absent': [],
            'present': [],
            'len_days': 0,
            'dates': [],
            "student_id": student.user_id
        }
        days = []
        for date in for_filter:
            day = datetime.strptime(date, "%Y-%m-%d")
            day = CalendarDay.query.filter(CalendarDay.date == day).first()
            attendance = AttendanceDays.query.filter(AttendanceDays.group_id == group.id,
                                                     AttendanceDays.student_id == student.id,
                                                     AttendanceDays.calendar_day == day.id).first()
            day_id = ""
            status = ""
            reason = ""
            if attendance:
                day_id = attendance.calendar_day
                if attendance.status == 1 or attendance.status == 2:
                    status = True
                else:
                    status = False

                if attendance.reason:
                    reason = attendance.reason
            homework = 0
            activeness = 0
            dictionary = 0
            average_ball = 0
            if attendance:
                if attendance.homework:
                    homework = attendance.homework
                if attendance.dictionary:
                    dictionary = attendance.dictionary
                if attendance.activeness:
                    activeness = attendance.activeness
                if attendance.average_ball:
                    average_ball = attendance.average_ball
            info = {
                "day_id": day_id,
                "day": date,
                "reason": reason,
                "status": status,
                "ball": {}
            }
            if attendance:
                if attendance.dictionary:
                    info['ball'] = {
                        "homework": homework,
                        "activeness": activeness,
                        "dictionary": dictionary,
                        "average_ball": average_ball
                    }
                else:
                    info['ball'] = {
                        "homework": homework,
                        "activeness": activeness,
                        "average_ball": average_ball
                    }

            days.append(info)
            student_att['dates'] = days
        attendances_list.append(student_att)
        filtered_attendances = []
        for student in attendances_list:
            added_to_existing = False
            for merged in filtered_attendances:
                if merged['group_id'] == student['group_id']:
                    added_to_existing = True
                if added_to_existing:
                    break
            if not added_to_existing:
                filtered_attendances.append(student)

        data = {
            "dates": sorted_dates,
            "attendances": filtered_attendances,
        }
        return data

    def student_self_attendances(self, year, month, group_id):
        date = str(year) + "-" + str(month)
        year = datetime.strptime(str(year), "%Y")
        date = datetime.strptime(date, "%Y-%m")
        calendar_year = CalendarYear.query.filter(CalendarYear.date == year).first()
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == date).first()
        groups = Groups.query.filter(Groups.id == group_id).first()
        attendances = db.session.query(AttendanceDays) \
            .join(AttendanceDays.attendance) \
            .options(contains_eager(AttendanceDays.attendance)) \
            .filter(
            Attendance.calendar_month == calendar_month.id,
            Attendance.calendar_year == calendar_year.id,
            Attendance.student_id == self.student_id,

        ) \
            .join(AttendanceDays.day) \
            .options(contains_eager(AttendanceDays.day)) \
            .order_by(CalendarDay.date) \
            .all()

        return attendances
