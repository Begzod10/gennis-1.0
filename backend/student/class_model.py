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
        FULL RECALCULATION of payment distribution.

        Process:
        1. Get ALL payments ever made
        2. Get ALL attendance records (reset them all)
        3. Redistribute payments from scratch across all records (FIFO order)
        4. Mark records as paid/unpaid based on available funds

        This is a full reset/recalculation, not incremental updates.
        """
        try:
            # Get student data
            student = Students.query.filter_by(id=self.student_id).first()
            if not student:
                raise ValueError(f"Student {self.student_id} not found")

            # Calculate total available funds using SQL aggregation
            funds_data = self._calculate_available_funds()

            # Calculate total income
            total_funds = (
                    funds_data['total_payments'] +
                    (student.old_money or 0)
            )

            # Calculate deductions
            deductions = (
                    funds_data['total_book_payments'] +
                    abs(student.old_debt or 0)
            )

            # Available funds for attendance
            available_for_attendance = total_funds - deductions

            # ✅ Get ALL attendance records (we're recalculating everything)
            all_attendances = AttendanceHistoryStudent.query.filter(
                AttendanceHistoryStudent.student_id == self.student_id
            ).order_by(AttendanceHistoryStudent.id).all()

            # ✅ Reset and redistribute from scratch
            distribution_result = self._redistribute_all_payments(
                all_attendances,
                available_for_attendance
            )

            # Store remaining funds as extra_payment
            student.extra_payment = distribution_result['remaining'] if distribution_result['remaining'] > 0 else 0

            # Single commit for all changes
            db.session.commit()

            return {
                'success': True,
                'total_funds': total_funds,
                'deductions': deductions,
                'available': available_for_attendance,
                'records_processed': distribution_result['records_processed'],
                'fully_paid': distribution_result['fully_paid'],
                'partially_paid': distribution_result['partially_paid'],
                'unpaid': distribution_result['unpaid'],
                'remaining': distribution_result['remaining'],
                'extra_payment': student.extra_payment
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    def _redistribute_all_payments(self, attendance_records, available_funds):
        """
        FULL redistribution of all payments across all attendance records.
        Resets all payment/remaining_debt/status fields and recalculates from scratch.

        Args:
            attendance_records: ALL attendance records (not filtered)
            available_funds: Total funds available to distribute

        Returns:
            dict: {
                'records_processed': int,
                'fully_paid': int,
                'partially_paid': int,
                'unpaid': int,
                'remaining': Decimal
            }
        """
        remaining_funds = available_funds
        records_processed = 0
        fully_paid = 0
        partially_paid = 0
        unpaid = 0

        for attendance in attendance_records:
            total_debt = abs(attendance.total_debt or 0)

            if total_debt <= 0:
                # No debt on this record - mark as paid with 0 payment
                attendance.status = True
                attendance.remaining_debt = 0
                attendance.payment = 0
                records_processed += 1
                continue

            if remaining_funds <= 0:
                # ✅ No funds left - mark as UNPAID with full debt remaining
                attendance.status = False
                attendance.remaining_debt = -total_debt  # Negative = debt
                attendance.payment = 0
                unpaid += 1
                records_processed += 1
                continue

            if remaining_funds >= total_debt:
                # ✅ Full payment available
                attendance.status = True
                attendance.remaining_debt = 0
                attendance.payment = total_debt
                remaining_funds -= total_debt
                fully_paid += 1

            else:
                # ✅ Partial payment
                attendance.status = False

                # How much we can pay
                amount_paid = remaining_funds

                # How much will still be owed
                still_owed = total_debt - amount_paid

                # Update fields
                attendance.remaining_debt = -still_owed  # Negative indicates debt
                attendance.payment = amount_paid

                remaining_funds = 0
                partially_paid += 1

            records_processed += 1

        return {
            'records_processed': records_processed,
            'fully_paid': fully_paid,
            'partially_paid': partially_paid,
            'unpaid': unpaid,
            'remaining': remaining_funds
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

        student = Students.query.filter_by(id=self.student_id).first()
        attendance_history = AttendanceHistoryStudent.query.filter(
            AttendanceHistoryStudent.student_id == self.student_id,
        ).all()
        payments = StudentPayments.query.filter(StudentPayments.student_id == self.student_id).all()
        book_payments = BookPayments.query.filter(BookPayments.student_id == self.student_id).all()
        all_payment = 0
        all_debt = 0
        old_money = 0
        old_debt = 0
        bk_payments = 0
        for book in book_payments:
            bk_payments += book.payment_sum
        if student.old_debt:
            old_debt = student.old_debt
        if student.old_money:
            old_money = student.old_money
        for attendance in attendance_history:

            if attendance.total_debt:
                all_debt += attendance.total_debt
        for pay in payments:
            all_payment += pay.payment_sum
        result = (all_payment + old_money) - (abs(all_debt) + abs(old_debt) + abs(bk_payments))

        # if result == 0:
        #     result = student.extra_payment
        # student_excuse = StudentExcuses.query.filter(StudentExcuses.student_id == self.student_id,
        #                                              StudentExcuses.to_date > calendar_day.date).order_by(
        #     desc(StudentExcuses.id)).first()
        if result == None:
            result = 0
        Users.query.filter(Users.id == student.user_id).update({'balance': result})

        db.session.commit()

        user = Users.query.filter(Users.id == student.user_id).first()
        if student.debtor != 4:

            if user.balance >= 0:
                Students.query.filter_by(id=self.student_id).update({"debtor": 0})
            if user.balance < 0:
                Students.query.filter_by(id=self.student_id).update({"debtor": 1})
            if student.combined_debt:
                if -user.balance >= -student.combined_debt:
                    Students.query.filter_by(id=self.student_id).update({"debtor": 2})

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
