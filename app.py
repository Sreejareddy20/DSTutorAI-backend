import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import get_connection
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# --- AI SETUP (GIVING YOU CHAT-GPT POWER) ---
# Paste your DSTUTOR API Key here
api_key = "AIzaSyAW9Q8iMoPVnTKh6HpZyAqvfv4R1rEaEF4"
genai.configure(api_key=api_key)
print(f"🚀 SERVER STARTING: Using API Key ending in ...{api_key[-4:]}")

# --- THE MOST STABLE SETUP ---
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

# EMAIL OTP FUNCTION
def send_otp_email(receiver_email, otp):
    sender_email = "dstutorai@gmail.com"
    sender_password = "bvne dvmb nrnq yckn"
    subject = "OTP Verification Code - DS Tutor AI"
    body = f"Hello,\n\nYour OTP code for DS Tutor AI is: {otp}\n\nThis code will expire shortly. If you did not request this, please ignore this email.\n\nBest regards,\nDS Tutor Team"
    
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email
        
        print(f"DEBUG: Attempting to send OTP to {receiver_email}...")
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.set_debuglevel(1)  # Enable debug output
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        
        print(f"DEBUG: OTP successfully sent to {receiver_email}")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to send email to {receiver_email}. Reason: {str(e)}")
        # We don't raise the error here to avoid crashing the main thread, 
        # but the log will tell us exactly why it failed.

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
        raw_error = str(e)
        print(f"DEBUG: RAW ERROR FROM GOOGLE: {raw_error}")
        if "429" in raw_error:
            answer = "I've temporarily reached my AI usage limit. Please wait about 1 minute and try again. I'll be ready to help shortly!"
        else:
            # Let's show a bit more detail to help your developer debug
            answer = f"AI Brain Error: {raw_error[:100]}... Please ask your developer to check the server logs."

    # 2. Save everything to your database history (For the history screen)
    connection = get_connection()
    cursor = connection.cursor()
    insert_query = "INSERT INTO chat_history (user_id, question, answer, created_at) VALUES (%s, %s, %s, %s)"
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(insert_query, (user_id, question, answer, current_time))
    connection.commit()
    cursor.close()
    connection.close()

    # 3. Send the AI's smart answer back to the phone
    return jsonify({
        "question": question,
        "answer": answer,
        "created_at": current_time
    })

# --- ALL OTHER ROUTES (Keep these for Login/Register) ---

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

@app.route("/verify_reset_otp", methods=["POST"])
def verify_reset_otp():
    # Same logic as verify_otp but specific endpoint for Android/Web clarity
    return verify_otp()

@app.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.json
    email = data.get("email")
    new_password = data.get("password")
    
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
    connection.commit()
    
    if cursor.rowcount > 0:
        response = {"message": "Password updated successfully"}
        status = 200
    else:
        response = {"message": "Error updating password"}
        status = 400
        
    cursor.close()
    connection.close()
    return jsonify(response), status

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email, password = data.get("email").strip(), data.get("password").strip()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s AND verified=1", (email, password))
    user = cursor.fetchone()
    if user:
        response = {"message": "Login successful", "name": user["name"], "user_id": user["id"]}
    else:
        response = {"message": "Invalid credentials"}
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
    except Exception as e:
        print(f"Update Profile Error: {e}")
        response = {"message": "Error updating profile (Email might already exist)"}
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

@app.route("/delete_chat/<int:chat_id>", methods=["DELETE"])
def delete_single_chat(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE id = %s", (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/clear_chat_history/<int:user_id>", methods=["DELETE"])
def clear_all_history(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/delete_account/<int:user_id>", methods=["DELETE"])
def delete_account(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Delete associated chat history
        cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
        # 2. Delete user account
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        response = {"message": "Account deleted successfully"}
    except Exception as e:
        print(f"Delete Account Error: {e}")
        response = {"message": "Error deleting account"}
    finally:
        cursor.close()
        conn.close()
    return jsonify(response)

if __name__ == "__main__":
    # Running on port 8024 as specified by the hosting link
    app.run(host="0.0.0.0", port=8024, debug=True)
