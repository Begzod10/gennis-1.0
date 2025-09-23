from backend.parent.crud import *


@crud_parent_bp.route('/crud/update-by-username', methods=['PUT'])
def update_parent_by_username():
    data = request.json
    username = data.get("username")
    if not username:
        return jsonify({"error": "username kerak"}), 400

    user = Users.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User topilmadi"}), 404

    parent = Parent.query.filter_by(user_id=user.id).first()
    if not parent:
        return jsonify({"error": "Parent topilmadi"}), 404

    if 'name' in data:
        user.name = data['name']
    if 'surname' in data:
        user.surname = data['surname']
    if 'address' in data:
        user.address = data['address']
    if 'born_date' in data:
        user.born_day = data['born_date'][8:10]
        user.born_month = data['born_date'][5:7]
        user.born_year = data['born_date'][0:4]
    if 'username' in data:
        user.username = data['username']

    db.session.commit()
    return jsonify(parent.convert_json())


@crud_parent_bp.route('/crud/delete-by-username', methods=['DELETE'])
def delete_parent_by_username():
    data = request.json
    username = data.get("username")
    if not username:
        return jsonify({"error": "username kerak"}), 400

    user = Users.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User topilmadi"}), 404

    parent = Parent.query.filter_by(user_id=user.id).first()
    if not parent:
        return jsonify({"error": "Parent topilmadi"}), 404

    parent.students = []
    user.deleted = True
    db.session.commit()

    return jsonify({"message": "Parent deleted successfully (gennis)"})
