from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
import logging
from src.models.user import User, db

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
@cross_origin()
def get_users():
    """Get all users with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        users = User.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'total': users.total,
                'pages': users.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/users', methods=['POST'])
@cross_origin()
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        if not data.get('username') or not data.get('email'):
            return jsonify({'error': 'Username and email are required'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | 
            (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'User with this username or email already exists'}), 409
        
        user = User(username=data['username'], email=data['email'])
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User created successfully: {user.username}")
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@cross_origin()
def get_user(user_id):
    """Get a specific user by ID."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@cross_origin()
def update_user(user_id):
    """Update a specific user."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Check for duplicate username/email if being updated
        if 'username' in data and data['username'] != user.username:
            existing = User.query.filter(User.username == data['username']).first()
            if existing:
                return jsonify({'error': 'Username already exists'}), 409
        
        if 'email' in data and data['email'] != user.email:
            existing = User.query.filter(User.email == data['email']).first()
            if existing:
                return jsonify({'error': 'Email already exists'}), 409
        
        # Update user fields
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        
        db.session.commit()
        
        logger.info(f"User updated successfully: {user.username}")
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@cross_origin()
def delete_user(user_id):
    """Delete a specific user."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        username = user.username  # Store for logging
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"User deleted successfully: {username}")
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
