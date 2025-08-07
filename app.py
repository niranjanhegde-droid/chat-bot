import markdown
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import requests

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_default_fallback_secret_key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import db and models
from models import db, User, Chat

# Initialize SQLAlchemy with app
db.init_app(app)

# Get OpenRouter API key
API_KEY = os.getenv("OPENROUTER_API_KEY")

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(username=username).first():
            return "User already exists."

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('chat'))

        return "Invalid credentials."

    return render_template('login.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    response = None

    if request.method == 'POST':
        prompt = request.form.get('prompt', '')


        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yourdomain.com",
            "X-Title": "Flask Chatbot"
        }

        data = {
            "model": "meta-llama/llama-3-70b-instruct",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

        if r.status_code == 200:
            import markdown
            raw_response = r.json()['choices'][0]['message']['content']
            response = markdown.markdown(raw_response)

            chat = Chat(user_id=user.id, prompt=prompt, response=response)
            db.session.add(chat)
            db.session.commit()
        else:
            response = f"Error: {r.status_code} - {r.text}"

    history = Chat.query.filter_by(user_id=user.id).order_by(Chat.timestamp.desc()).all()
    return render_template('chat.html', response=response, history=history, user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
