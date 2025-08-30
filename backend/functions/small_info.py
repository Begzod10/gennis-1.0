def user_photo_folder():
    folder = "staticfiles/img_folder"
    return folder


def advantages_photo_folder():
    folder = "staticfiles/advantages"
    return folder


def news_photo_folder():
    folder = "staticfiles/news"
    return folder


def gallery_folder():
    folder = "staticfiles/gallery"
    return folder


def user_contract_folder():
    folder = "staticfiles/contract_pdf"
    return folder


def home_design():
    folder = "staticfiles/home_design"
    return folder


def certificate():
    folder = "staticfiles/certificates"
    return folder


def link_img():
    folder = "staticfiles/link_img"
    return folder


def teacher_certificate():
    folder = "staticfiles/teacher_certificate"
    return folder


def room_images():
    folder = "staticfiles/room"
    return folder


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'svg', 'xlsx', 'docx', 'doc', 'zip', 'rar'}


def checkFile(filename):
    value = '.' in filename

    type_file = filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    return value and type_file
