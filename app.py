import os
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import get_connection
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText

# Load secret Keys from .env file
load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# --- AI SETUP ---
api_key = os.getenv("GEMINI_API_KEY") 
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY NOT FOUND IN .env FILE!")
else:
    genai.configure(api_key=api_key)

# --- AI TUTOR SETUP ---
model = genai.GenerativeModel(
    model_name='gemini-flash-latest',
    system_instruction="""
    You are a brilliant Data Structures and Algorithms Tutor.
    1. Answer any question related to Data Structures (Arrays, Lists, Stacks, Trees, Graphs, etc.).
    2. ALWAYS provide code implementations in BOTH Python and Java whenever you explain a concept.
    3. Use technical but easy-to-understand language.
    4. For non-Data Structure topics, politely explain: 'I am a specialized Data Structures Tutor, I can only help you with DS topics!'
    """
)

# EMAIL OTP FUNCTION (SECURED)
def send_otp_email(receiver_email, otp):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    subject = "OTP Verification Code - DS Tutor AI"
    body = f"Hello,\n\nYour OTP code for DS Tutor AI is: {otp}\n\nThis code will expire shortly. Best regards, DS Tutor Team"
    
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Error sending email: {str(e)}")

@app.route("/")
def home():
    return send_from_directory('frontend', 'splash.html')

# --- SMART AI CHAT API ---
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = data.get("user_id")
    question = data.get("question")
    try:
        response = model.generate_content(question)
        answer = response.text
    except Exception as e:
        answer = f"AI Error: {str(e)[:100]}"

    connection = get_connection()
    cursor = connection.cursor()
    insert_query = "INSERT INTO chat_history (user_id, question, answer, created_at) VALUES (%s, %s, %s, %s)"
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(insert_query, (user_id, question, answer, current_time))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"question": question, "answer": answer, "created_at": current_time})

# --- USER MANAGEMENT ROUTES ---

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    otp = str(random.randint(100000, 999999))
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password, otp) VALUES (%s,%s,%s,%s)", (name, email, password, otp))
        connection.commit()
        send_otp_email(email, otp)
        response = {"message": "User registered successfully. OTP sent"}
    except Exception:
        response = {"message": "Email already exists"}
    cursor.close()
    connection.close()
    return jsonify(response)

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json
    email, otp = data.get("email"), data.get("otp")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s AND otp=%s", (email, otp))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET verified=TRUE WHERE email=%s", (email,))
        connection.commit()
        response = {"message": "OTP Verified"}
    else:
        response = {"message": "Invalid OTP"}
    cursor.close()
    connection.close()
    return jsonify(response)

@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email").strip()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    if user:
        otp = str(random.randint(100000, 999999))
        cursor.execute("UPDATE users SET otp=%s WHERE email=%s", (otp, email))
        connection.commit()
        send_otp_email(email, otp)
        response = {"message": "Reset OTP sent to your email"}
        status = 200
    else:
        response = {"message": "Email not found"}
        status = 404
    cursor.close()
    connection.close()
    return jsonify(response), status

@app.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.json
    email, new_password = data.get("email"), data.get("password")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
    connection.commit()
    response = {"message": "Password updated successfully"} if cursor.rowcount > 0 else {"message": "Error"}
    cursor.close()
    connection.close()
    return jsonify(response)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email, password = data.get("email").strip(), data.get("password").strip()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s AND verified=1", (email, password))
    user = cursor.fetchone()
    response = {"message": "Login successful", "name": user["name"], "user_id": user["id"]} if user else {"message": "Invalid credentials"}
    cursor.close()
    connection.close()
    return jsonify(response)

@app.route("/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as count FROM chat_history WHERE user_id=%s", (user_id,))
    chat_count = cursor.fetchone()["count"]
    cursor.close()
    connection.close()
    if user:
        user["chats_completed"] = chat_count
        return jsonify(user)
    return jsonify({"message": "User not found"}), 404

@app.route("/update_profile", methods=["POST"])
def update_profile():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name")
    email = data.get("email")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, user_id))
        connection.commit()
        response = {"message": "Profile updated successfully"}
    except:
        response = {"message": "Error"}
    finally:
        cursor.close()
        connection.close()
    return jsonify(response)

@app.route("/chat_history/<int:user_id>", methods=["GET"])
def get_chat_history(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, question, answer, created_at FROM chat_history WHERE user_id=%s ORDER BY id DESC", (user_id,))
    chats = cursor.fetchall()
    cursor.close()
    connection.close()
    for chat in chats:
        if isinstance(chat.get('created_at'), datetime):
            chat['created_at'] = chat['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(chats)

@app.route("/delete_account/<int:user_id>", methods=["DELETE"])
def delete_account(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        response = {"message": "Account deleted"}
    except:
        response = {"message": "Error"}
    finally:
        cursor.close()
        conn.close()
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8024, debug=True)
