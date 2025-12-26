# Automation Server

This is a Python-based automation server designed to schedule, execute, and monitor Python scripts. It features a React frontend (for the headless server) and a PySide6 GUI (for the desktop server).

## Features

*   **Script Scheduling**: Execute scripts based on defined schedules.
*   **BigQuery Integration**: Syncs execution logs and metrics to BigQuery.
*   **Real-time Monitoring**: Dashboard to view script status, logs, and next execution times.
*   **Mock Mode**: Ability to run in "Simulation Mode" for testing without affecting production data.
*   **Headless & GUI Modes**: Run as a background service or a desktop application.

## Setup

1.  **Clone the repository**.
2.  **Create a `.env` file** based on `.env.example` and fill in your specific paths and project IDs.
    *   **Important**: The `.env` file is NOT excluded from git but contains sensitive info in the original setup. Ensure you do not commit secrets if you fork this. (Note: The provided `.gitignore` excludes `.env`).
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the Server**:
    *   **Headless**: `python Server.py`
    *   **Desktop GUI**: `python Servidor.py`

## Project Structure

*   `Server.py`: Main backend logic (FastAPI, Threading) for the headless server.
*   `Servidor.py`: PySide6 Desktop Application.
*   `automacoes_exec.py`: Helper for BigQuery execution logging.
*   `web_frontend/`: React source code for the web dashboard.

## License

MIT License. See `LICENSE` file.
