# from backend.functions.utils import find_calendar_date
from datetime import datetime

from backend.models.models import Column, Integer, db, String, ForeignKey, Boolean, desc, DateTime, relationship


class LeadInfos(db.Model):
    __tablename__ = "lead_infos"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('lead.id'))
    comment = Column(String)
    day = Column(DateTime)
    added_date = Column(DateTime)
    audio_url = Column(String)
    records = relationship("LeadInfosRecord", backref="lead_infos", order_by="LeadInfosRecord.id")

    def convert_json(self, entire=False):
        audio_url = None
        if self.audio_url:
            if not self.audio_url.startswith('/'):
                audio_url = f"/media/{self.audio_url}"
            elif 'media/' in self.audio_url:
                relative_path = self.audio_url.split('media/')[-1]
                audio_url = f"/media/{relative_path}"
        if entire:
            return {
                "id": self.id,
                "lead_id": self.lead_id,
                "comment": self.comment,
                "name": self.lead.name,
                "phone": self.lead.phone,
                "added_date": self.added_date.strftime("%Y-%m-%d"),
                "date": self.day.strftime("%Y-%m-%d") if self.day else None,
                "audio_url": audio_url,
                "audios_list": [record.convert_json() for record in self.records],
                "duration": self.records[len(self.records) - 1].duration
            }
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "comment": self.comment,
            "name": self.lead.name,
            "phone": self.lead.phone,
            "added_date": self.added_date.strftime("%Y-%m-%d"),
            "date": self.day.strftime("%Y-%m-%d") if self.day else None,
            "audio_url": audio_url,
            "duration": self.records[len(self.records) - 1].duration if self.records else None
        }

    def add(self):
        db.session.add(self)
        db.session.commit()


class LeadInfosRecord(db.Model):
    __tablename__ = "lead_infos_record"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('lead_infos.id'))
    audio_url = Column(String)
    client_number = Column(String)
    diversion = Column(String)
    duration = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    wait_time = Column(String)
    comment = Column(String)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        audio_url = None
        if self.audio_url:
            if not self.audio_url.startswith('/'):
                audio_url = f"/media/{self.audio_url}"
            elif 'media/' in self.audio_url:
                relative_path = self.audio_url.split('media/')[-1]
                audio_url = f"/media/{relative_path}"
        return {
            "id": self.id,
            "audio_url": audio_url,
            "client_number": self.client_number,
            "diversion": self.diversion,
            "duration": self.duration,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "wait_time": self.wait_time,
            "comment": self.comment,
            "name": self.lead_infos.lead.name,
            "phone": self.lead_infos.lead.phone
        }


class Lead(db.Model):
    __tablename__ = "lead"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    deleted = Column(Boolean, default=False)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    comment = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'))
    infos = relationship("LeadInfos", backref="lead", order_by=desc(LeadInfos.id))
    recommended_by = relationship(
        "LeadRecomended",
        foreign_keys="[LeadRecomended.recommended_id]",
        backref="recommended_lead"
    )
    recommendations = relationship(
        "LeadRecomended",
        foreign_keys="[LeadRecomended.lead_id]",
        backref="recommender_lead"
    )

    def convert_json(self, entire=False):

        info = LeadInfos.query.filter(LeadInfos.lead_id == self.id).order_by(desc("id")).first()
        day = info.day if info else self.day.date
        if info:
            lead_day = int(day.strftime("%d")) if day else 0
            current_month = int(datetime.today().strftime("%m"))
            current_day = int(datetime.today().strftime("%d"))
            lead_month = int(day.strftime("%m")) if day else 0
            if current_month == lead_month:
                index = current_day - lead_day
                if index > 2:
                    index = 2
                if index < 0:
                    index = 0
            else:
                index = 2
        else:
            index = 2
        history = []
        completed = []
        if self.infos:
            for info in self.infos:
                history.append(info.convert_json())

        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "day": self.day.date.strftime("%Y-%m-%d"),
            "deleted": self.deleted,
            "comment": self.comment,
            "status": ['green', 'yellow', 'red'][index],
            "history": history,
            "subjects": [subject.convert_json() for subject in self.subject]
        }

    def add(self):
        db.session.add(self)
        db.session.commit()


class LeadRecomended(db.Model):
    __tablename__ = "lead_recommended"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('lead.id'))
    recommended_id = Column(Integer, ForeignKey('lead.id'))


db.Table('lead_subject',
         db.Column('lead_id', db.Integer, db.ForeignKey('lead.id')),
         db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
         )
