from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies
)
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON in request"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"msg": "Email and password must be strings"}), 400

    email = email.strip().lower()
    password = password.strip()

    if not email or not password:
        return jsonify({"msg": "Email and password cannot be empty"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "User with this email already exists"}), 409

    hashed_password = generate_password_hash(password)

    new_user = User(email=email, password_hash=hashed_password)
    db.session.add(new_user)
    try:
        db.session.commit()
        return jsonify({"msg": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during user registration: {e}")
        return jsonify({"msg": "An error occurred during registration"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON in request"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"msg": "Email and password must be strings"}), 400

    email = email.strip().lower()
    password = password.strip()

    if not email or not password:
        return jsonify({"msg": "Email and password cannot be empty"}), 400

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        response = jsonify({"msg": "Login successful"})
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response, 200
    else:
        return jsonify({"msg": "Bad email or password"}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    response = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)

    response = jsonify({"msg": "Token refreshed"})
    set_access_cookies(response, new_access_token)
    return response, 200

@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user:
        return jsonify(logged_in_as=user.email), 200
    return jsonify({"msg": "User not found"}), 404