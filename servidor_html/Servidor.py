import os
import sys
import time
import threading
import webbrowser
import subprocess

# Ensure the script execution directory is the root 'servidor_html'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.chdir(BASE_DIR)

# CONFIGURAÇÃO DE MODO OFFLINE
# True  = Modo Offline (Dados Fictícios, sem BigQuery)
# False = Modo Online (Conecta no BigQuery, envia emails reais)
SERVIDOR_OFFLINE = True 

# Inject into environment for Config to pick up
os.environ["SERVIDOR_OFFLINE"] = str(SERVIDOR_OFFLINE)

def install_dependencies():
    """Installs dependencies from requirements.txt if uvicorn is missing."""
    print("=== Checking dependencies... ===")
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_path):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
            print("=== Dependencies installed successfully! ===")
        except subprocess.CalledProcessError as e:
            print(f"=== Failed to install dependencies: {e} ===")
            sys.exit(1)
    else:
        print("=== requirements.txt not found. Proceeding at own risk... ===")

try:
    import uvicorn
except ImportError:
    install_dependencies()
    import uvicorn

import uvicorn

def open_browser():
    """Waits for server startup then opens the browser."""
    time.sleep(1.5) # Wait for Uvicorn to start
    print("=== Opening Browser at http://localhost:8000 ===")
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print(f"=== Starting Servidor Web in {BASE_DIR} ===")
    
    # Start browser thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Uvicorn Server
    # reload=True is useful for dev, but we can disable for "production" feel if preferred. 
    # Keeping True as user might be editing.
    try:
        uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("=== Server Stopped ===")
