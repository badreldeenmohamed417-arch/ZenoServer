from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def home():
    return "MasterKey Desktop is alive!"


@app.get("/api/discover")
def discover():
    return jsonify({
        "name": "MasterKey Desktop",
        "status": "online"
    })


app.run(host="0.0.0.0", port=8765)