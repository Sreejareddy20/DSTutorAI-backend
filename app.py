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

# --- ALL OTHER ROUTES (Keep these as they are) ---
# ... (Register, Login, Profile, etc.) ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8024, debug=True)
