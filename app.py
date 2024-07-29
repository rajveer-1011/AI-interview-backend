from flask import Flask
from flask_socketio import SocketIO, emit
from gtts import gTTS
import io
import time
import base64
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

questions = [
    "What is your experience with Python?",
    "Can you describe a challenging project you've worked on?",
    "How do you handle tight deadlines?",
    "What is your approach to debugging code?",
    "What are your career goals?"
]
current_question_index = 0
is_waiting_for_response = False
waiting_for_yes = False
last_transcript_time = time.time()  
prompt_interval = 8 

def emit_question():
    global current_question_index, is_waiting_for_response, last_transcript_time
    if current_question_index < len(questions):
        question_text = f"Question {current_question_index + 1}: {questions[current_question_index]}"
        tts = gTTS(text=question_text, lang='en')
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)
        encoded_audio = base64.b64encode(audio_stream.getvalue()).decode('utf-8') 
        socketio.emit('audio', {'audio_data': encoded_audio})
        socketio.emit('question', {'question': question_text})
        is_waiting_for_response = True
        last_transcript_time = time.time()
    else:
        end_interview()

def prompt_user():
    question_prompt = "Please respond to the question or say 'yes' to move to the next question."
    tts = gTTS(text=question_prompt, lang='en')
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    audio_stream.seek(0)
    encoded_audio = base64.b64encode(audio_stream.getvalue()).decode('utf-8')  
    socketio.emit('audio', {'audio_data': encoded_audio})
    socketio.emit('question', {'question': question_prompt})

def handle_timeout():
    global is_waiting_for_response, last_transcript_time, waiting_for_yes
    print(f"Handle timeout: is_waiting_for_response={is_waiting_for_response}, last_transcript_time={last_transcript_time}, waiting_for_yes={waiting_for_yes}")
    
    if is_waiting_for_response and time.time() - last_transcript_time > prompt_interval:
        print("Timeout reached. Prompting user.")
        prompt_user()
        last_transcript_time = time.time() 

    elif waiting_for_yes and time.time() - last_transcript_time > prompt_interval:
        print("Waiting for 'yes' and timeout reached. Prompting user.")
        prompt_user()
        last_transcript_time = time.time() 

@socketio.on('start_interview')
def handle_start_interview():
    global waiting_for_yes, last_transcript_time
    welcome_text = "Welcome to the interview session. To proceed, say 'yes'."
    tts = gTTS(text=welcome_text, lang='en')
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    audio_stream.seek(0)
    encoded_audio = base64.b64encode(audio_stream.getvalue()).decode('utf-8') 
    socketio.emit('audio', {'audio_data': encoded_audio})
    waiting_for_yes = True
    last_transcript_time = time.time() 

@socketio.on('transcript')
def handle_transcript(data):
    global current_question_index, is_waiting_for_response, last_transcript_time, waiting_for_yes

    transcript = data['data'].lower()
    print(f"Received transcript: {transcript}")

    last_transcript_time = time.time()

    if waiting_for_yes:
        if 'yes' in transcript:
            print("Received 'yes if', proceeding to next question.")
            waiting_for_yes = False
            emit_question()
    elif is_waiting_for_response:
        if 'yes' in transcript:
            print("Received 'yes elif', moving to the next question.")
            current_question_index += 1
            is_waiting_for_response = False
            if current_question_index < len(questions):
                emit_question()
            else:
                end_interview()

def prompt_check():
    while True:
        socketio.sleep(1)  
        handle_timeout()

def end_interview():
    end_text = "Thank you for participating in the interview."
    tts = gTTS(text=end_text, lang='en')
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    audio_stream.seek(0)
    encoded_audio = base64.b64encode(audio_stream.getvalue()).decode('utf-8')  
    socketio.emit('audio', {'audio_data': encoded_audio})
    global current_question_index, is_waiting_for_response, waiting_for_yes
    current_question_index = 0
    is_waiting_for_response = False
    waiting_for_yes = False
    last_transcript_time = time.time()  

if __name__ == '__main__':
    prompt_thread = Thread(target=prompt_check)
    prompt_thread.daemon = True 
    prompt_thread.start()

    socketio.run(app, port=5000)
