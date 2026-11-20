import asyncio
import httpx
import os
import subprocess
import webbrowser
import psutil
import json
import urllib.parse
import pyautogui
import threading
import speech_recognition as sr
import pyttsx3
import time
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="R.U.B.I. Core System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global States for UI Broadcasting ---
connected_websockets = set()
main_loop = None

def speak(text: str):
    def run_tts():
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            if "zira" in voice.name.lower() or "female" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', 170)
        clean_text = text.replace('*', '').replace('#', '').replace('`', '')
        engine.say(clean_text)
        engine.runAndWait()
        
    threading.Thread(target=run_tts, daemon=True).start()

async def broadcast_to_ui(msg_type: str, sender: str = "", text: str = ""):
    if not main_loop:
        return
    payload = json.dumps({"type": msg_type, "sender": sender, "text": text})
    dead_clients = set()
    for ws in connected_websockets:
        try:
            await ws.send_text(payload)
        except:
            dead_clients.add(ws)
    for ws in dead_clients:
        connected_websockets.remove(ws)

# --- AI Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
AI_MODEL = "qwen2.5:1.5b" 

SYSTEM_PROMPT = """You are R.U.B.I. (Responsive Utility & Behavioral Intelligence), a highly advanced, professional, and highly efficient personal AI desktop assistant running on a Windows system. 
Your interface is a cinematic holographic terminal. 
You are concise, highly intelligent, and speak with a calm, robotic, yet elegant tone. 
Never use emojis. Do not break character. Provide clear, direct, and brief answers. Never refer to yourself as an AI model created by OpenAI or Alibaba, you are R.U.B.I."""

DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")

def execute_system_command(command: str) -> str:
    command_lower = command.lower().strip()
    
    # --- 1. UPDATED: Ghost Typing Feature with Delay ---
    if command_lower.startswith("type ") or command_lower.startswith("write "):
        text_to_type = command_lower.replace("type ", "", 1).replace("write ", "", 1).strip()
        if text_to_type:
            # Wait 2 seconds so the user can ensure their cursor is focused in the target window
            time.sleep(2)
            # Type slightly slower for better Windows compatibility
            pyautogui.write(text_to_type, interval=0.04)
            pyautogui.press('enter')
            return f"System Action: Typed '{text_to_type}' on the keyboard."

    # --- 2. System Controls ---
    if command_lower in ["mute volume", "mute audio", "mute system"]:
        pyautogui.press("volumemute")
        return "System Action: Muted system audio."
    elif command_lower in ["increase volume", "volume up"]:
        pyautogui.press("volumeup", presses=5)
        return "System Action: Increased system volume."
    elif command_lower in ["decrease volume", "volume down"]:
        pyautogui.press("volumedown", presses=5)
        return "System Action: Decreased system volume."

    # --- 3. Screenshots & Folders ---
    if "take a screenshot" in command_lower or "capture screen" in command_lower:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"RUBI_Screenshot_{timestamp}.png"
        filepath = os.path.join(DESKTOP_PATH, filename)
        pyautogui.screenshot(filepath)
        return f"System Action: Captured screenshot and saved it to the desktop as {filename}."

    if command_lower.startswith("create folder"):
        folder_name = command_lower.replace("create folder", "").strip()
        if not folder_name:
            folder_name = "RUBI_New_Folder"
        folder_path = os.path.join(DESKTOP_PATH, folder_name)
        try:
            os.makedirs(folder_path, exist_ok=True)
            return f"System Action: Created a new folder named '{folder_name}' on the desktop."
        except Exception as e:
            return f"System Action: Failed to create folder. Error: {e}"

    # --- 4. Desktop Applications ---
    if command_lower.startswith("open notepad"):
        subprocess.Popen(["notepad.exe"])
        return "System Action: Launched Notepad."
    elif command_lower.startswith("open calculator") or command_lower == "open calc":
        subprocess.Popen(["calc.exe"])
        return "System Action: Launched Calculator."

    # --- 5. Browser & Searches ---
    if "search" in command_lower and "youtube" in command_lower:
        query = command_lower.replace("search", "").replace("on youtube", "").replace("in youtube", "").replace("youtube", "").strip()
        if query:
            encoded_query = urllib.parse.quote(query)
            webbrowser.open(f"https://www.youtube.com/results?search_query={encoded_query}")
            return f"System Action: Searched YouTube for '{query}'."

    if "search" in command_lower and "google" in command_lower:
        query = command_lower.replace("search", "").replace("on google", "").replace("in google", "").replace("google", "").strip()
        if query:
            encoded_query = urllib.parse.quote(query)
            webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
            return f"System Action: Searched Google for '{query}'."

    if command_lower.startswith("open "):
        target = command_lower.replace("open ", "").strip()
        target_clean = target.replace(" ", "")
        
        if target_clean not in ["notepad", "calculator", "calc"]:
            url = f"https://www.{target_clean}.com"
            webbrowser.open(url)
            return f"System Action: Opened website {target_clean}.com."

    return None

def get_system_metrics() -> str:
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    storage = psutil.disk_usage('/').percent
    return json.dumps({"type": "metrics", "cpu": cpu, "ram": ram, "storage": storage})

async def get_rubi_response(user_input: str, system_context: str = "") -> str:
    prompt_injection = user_input
    if system_context:
        prompt_injection = f"The user asked: '{user_input}'. The system automatically performed this action behind the scenes: '{system_context}'. Confirm to the user that you have completed this action smoothly and professionally."

    payload = {"model": AI_MODEL, "prompt": prompt_injection, "system": SYSTEM_PROMPT, "stream": False}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Error: Blank response generated by core.")
        except Exception as e:
            return f"System Error: AI generation failed. Code: {e}"

async def process_command_pipeline(command: str):
    await broadcast_to_ui("chat", "user", command)
    await broadcast_to_ui("status", text="PROCESSING...")
    
    action_result = execute_system_command(command)
    rubi_reply = await get_rubi_response(command, system_context=action_result)
    
    await broadcast_to_ui("chat", "rubi", rubi_reply)
    speak(rubi_reply)
    await broadcast_to_ui("status", text="AWAITING WAKE WORD...")

# --- Continuous OS-Level Audio Listener ---
def system_audio_listener():
    recognizer = sr.Recognizer()
    
    try:
        microphone = sr.Microphone()
    except Exception as e:
        print(f"[SYS ERROR] No microphone detected by Python: {e}")
        return
        
    print("[SYS] Calibrating microphone for background noise...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        recognizer.dynamic_energy_threshold = True
        
    print("[SYS] OS-Level Background Listening Active. (Waiting for 'Hey RUBI')")
    
    while True:
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
            
            text = recognizer.recognize_google(audio).lower()
            print(f"[HEARD] {text}")
            
            if "rubi" in text or "ruby" in text or "rooby" in text:
                command = text.replace("hey rubi", "").replace("hey ruby", "").replace("hi rubi", "").strip()
                
                if command and main_loop:
                    asyncio.run_coroutine_threadsafe(process_command_pipeline(command), main_loop)
                    
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception as e:
            print(f"[AUDIO ERROR] {e}")

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    threading.Thread(target=system_audio_listener, daemon=True).start()
    speak("System initialization complete. R.U.B.I. core online.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    print("[SYS] UI Dashboard connected securely.")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "GET_METRICS":
                await websocket.send_text(get_system_metrics())
                continue
                
            await process_command_pipeline(data)
            
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
        print("[SYS] UI Dashboard disconnected.")