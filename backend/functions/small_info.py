def user_photo_folder():
    folder = "static/img_folder"
    return folder


def advantages_photo_folder():
    folder = "static/advantages"
    return folder


def news_photo_folder():
    folder = "static/news"
    return folder


def gallery_folder():
    folder = "static/gallery"
    return folder


def user_contract_folder():
    folder = "static/contract_pdf"
    return folder


def home_design():
    folder = "static/home_design"
    return folder


def certificate():
    folder = "static/certificates"
    return folder


def link_img():
    folder = "static/link_img"
    return folder


def teacher_certificate():
    folder = "static/teacher_certificate"
    return folder


def room_images():
    folder = "static/room"
    return folder


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'svg', 'xlsx', 'docx', 'doc', 'zip', 'rar'}


def checkFile(filename):
    value = '.' in filename

    type_file = filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    return value and type_file
