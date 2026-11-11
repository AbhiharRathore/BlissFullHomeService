import os

from PROJECT import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode exposes an interactive console; enable it only explicitly for local work.
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", host="127.0.0.1", port=5010)
