import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.api.app import app

if __name__ == "__main__":
    print("=" * 50)
    print("NBA Lineup Optimizer")
    print("Server: http://127.0.0.1:8000")
    print("Health: http://127.0.0.1:8000/api/health")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False, threaded=True)
