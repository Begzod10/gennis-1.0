import requests
from app import db, app  # Import app instance
from backend.student.register_for_tes.models import Region, University, Faculty, School


def create_regions():
    try:
        regions = [
            {"id": 13, "name": "Toshkent viloyati"},
            {"id": 14, "name": "Toshkent shahri"},
        ]

        for region_data in regions:
            # Check if the region with this id already exists
            existing_region = Region.query.get(region_data["id"])
            if not existing_region:
                # Add region only if it doesn't exist
                region = Region(**region_data)
                db.session.add(region)

        # Commit all new additions at once
        db.session.commit()
        print("Regions created successfully.")
    except Exception as e:
        print(f"Error creating regions: {e}")
        db.session.rollback()


def create_universities():
    for region_id in [13, 14]:
        try:
            url = f"https://mandat.uzbmb.uz/Mandat2024/GetUniversitiesByRegion/?lang=uz&regionid={region_id}"
            response = requests.get(url)
            response.raise_for_status()
            for univ_data in response.json():
                university = University.query.filter_by(
                    name=univ_data["universityName"],
                    region_id=region_id,
                    university_id=univ_data["universityId"]
                ).first()
                if not university:
                    university = University(
                        name=univ_data["universityName"],
                        region_id=region_id,
                        university_id=univ_data["universityId"]
                    )
                    db.session.add(university)
                    db.session.commit()
            print(f"Universities for region {region_id} created successfully.")
        except requests.RequestException as req_err:
            print(f"Request error while creating universities for region {region_id}: {req_err}")
        except Exception as e:
            print(f"Error creating universities for region {region_id}: {e}")
            db.session.rollback()


def create_faculties():
    try:
        universities = University.query.all()
        for university in universities:
            url = f"https://mandat.uzbmb.uz/Mandat2024/GetFacultiesByUniversity/?universityid={university.university_id}"
            response = requests.get(url)
            response.raise_for_status()
            for fac_data in response.json():
                faculty = Faculty.query.filter_by(
                    name=fac_data["facultyname"],
                    university_id=university.id,
                    mvdir=str(fac_data["mvdir"])
                ).first()
                if not faculty:
                    faculty = Faculty(
                        name=fac_data["facultyname"],
                        university_id=university.id,
                        mvdir=str(fac_data["mvdir"])
                    )
                    db.session.add(faculty)
        db.session.commit()
        print("Faculties created successfully.")
    except requests.RequestException as req_err:
        print(f"Request error while creating faculties: {req_err}")
    except Exception as e:
        print(f"Error creating faculties: {e}")
        db.session.rollback()


def create_school():
    for i in range(1, 51):
        school = School.query.filter_by(number=i).first()
        if not school:
            new_school = School(number=i, name=f"{i} - Maktab")
            db.session.add(new_school)
    db.session.commit()

# Run the script within the application context
