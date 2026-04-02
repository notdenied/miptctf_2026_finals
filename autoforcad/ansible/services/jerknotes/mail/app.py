from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import os
from psycopg2 import sql
import psycopg2
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy.exc import OperationalError
import secrets

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://postgres:{os.getenv('DB_PASS')}@db:5432/postgres"
app.config['SECRET_KEY'] = str(secrets.randbits(128))

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class Mail_users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Mail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('mail_users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

@login_manager.user_loader
def load_user(user_id):
    return Mail_users.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if Mail_users.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = Mail_users(email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth.html')

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = Mail_users.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        return jsonify({'message': 'Login successful'}), 200

    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/logout', methods=['GET','POST'])
@login_required
def logout():
    logout_user()
    if request.method == 'POST' or request.is_json:
        return jsonify({'message': 'Logout successful'}), 200
    return render_template('auth.html')

@app.route('/mails', methods=['GET'])
@login_required
def get_mails():
    mail_id = request.args.get('id')
    if mail_id:
        try:
            mail_obj = Mail.query.filter_by(id=int(mail_id), recipient_id=current_user.id).first()
            if not mail_obj:
                return jsonify({'message': 'Not found'}), 404
            return jsonify({
                'id': mail_obj.id,
                'subject': mail_obj.subject,
                'content': mail_obj.content,
                'timestamp': mail_obj.timestamp.isoformat() if mail_obj.timestamp else None
            }), 200
        except Exception:
            return jsonify({'message': 'Bad request'}), 400

    mails = Mail.query.filter_by(recipient_id=current_user.id).order_by(Mail.timestamp.desc()).all()
    mails_data = [{'id': mail.id, 'subject': mail.subject, 'content': mail.content, 'timestamp': mail.timestamp.isoformat() if mail.timestamp else None} for mail in mails]

    return jsonify(mails_data), 200


@app.route('/mails/delete', methods=['POST'])
@login_required
def delete_mail():
    mail_id = request.args.get('id') or request.json and request.json.get('id')
    if not mail_id:
        return jsonify({'message': 'Missing id'}), 400
    try:
        mail_obj = Mail.query.filter_by(id=int(mail_id), recipient_id=current_user.id).first()
        if not mail_obj:
            return jsonify({'message': 'Not found'}), 404
        db.session.delete(mail_obj)
        db.session.commit()
        return jsonify({'message': 'Deleted'}), 200
    except Exception as e:
        return jsonify({'message': 'Delete failed'}), 500

@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/mails_page')
@login_required
def mails_page():
    return render_template('mails.html')


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
