import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.api.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 50)
    print("NBA Lineup Optimizer")
    print(f"Server: http://127.0.0.1:{port}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
