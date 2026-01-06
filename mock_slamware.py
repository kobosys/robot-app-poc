# mock_slamware.py
from flask import Flask, request, jsonify
import time
import uuid

app = Flask(__name__)

# 간단한 상태 저장
ACTIONS = {}  # action_id -> {"status": "...", "created": float}

@app.get("/api/multi-floor/map/v1/pois")
def pois():
    # 로봇에 POI가 있다고 가정
    return jsonify([
        {"poi_name": "A"},
        {"poi_name": "B"},
        {"poi_name": "C"},
    ])

@app.post("/api/core/motion/v1/actions")
def create_action():
    payload = request.get_json(force=True, silent=True) or {}
    
    print("CREATE_ACTION payload =", payload)
    action_id = str(uuid.uuid4())[:8]
    ACTIONS[action_id] = {"status": "running", "created": time.time(), "payload": payload}
    return jsonify({"action_id": action_id})

@app.get("/api/core/motion/v1/actions/<action_id>")
def get_action(action_id: str):
    if action_id not in ACTIONS:
        return jsonify({"status": "failed"}), 404

    # 2초 지나면 성공 처리
    created = ACTIONS[action_id]["created"]
    if time.time() - created > 2.0:
        ACTIONS[action_id]["status"] = "succeeded"
    return jsonify({"status": ACTIONS[action_id]["status"]})

@app.delete("/api/core/motion/v1/actions/:current")
def stop_current():
    # 가장 최근 action 하나를 canceled로 처리 (아주 단순)
    if ACTIONS:
        last_id = list(ACTIONS.keys())[-1]
        ACTIONS[last_id]["status"] = "canceled"
    return ("", 204)

if __name__ == "__main__":
    # Slamware 기본 포트처럼 1445로 띄움
    app.run(host="127.0.0.1", port=1445, debug=False)
