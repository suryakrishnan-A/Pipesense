"""
PipeSense & DrainPilot Swagger UI Documentation Application.

This application runs independently on Port 5002 in its own environment
and documents the PipeSense and DrainPilot REST APIs hosted on Port 5001.

No modifications to existing backend or configuration files are required.
"""

import os
import json
from flask import Flask, redirect, send_file, jsonify, request
from flask_cors import CORS
from swagger_ui import flask_api_doc

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(BASE_DIR, "openapi.yaml")
JSON_PATH = os.path.join(BASE_DIR, "openapi.json")

# Configure Swagger UI using swagger-ui-py
flask_api_doc(
    app,
    config_path=YAML_PATH,
    url_prefix="/docs",
    title="PipeSense & DrainPilot API Documentation"
)


@app.route("/")
def index():
    """Redirect root path directly to Swagger UI documentation."""
    return redirect("/docs/")


@app.route("/openapi.yaml", methods=["GET"])
def get_openapi_yaml():
    """Serve the raw OpenAPI 3.0 YAML specification."""
    return send_file(YAML_PATH, mimetype="text/yaml")


@app.route("/openapi.json", methods=["GET"])
def get_openapi_json():
    """Serve the raw OpenAPI 3.0 JSON specification."""
    return send_file(JSON_PATH, mimetype="application/json")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint indicating service status and documented target API."""
    return jsonify({
        "status": "UP",
        "service": "Swagger UI Documentation Service",
        "docs_url": "http://localhost:5002/docs/",
        "target_api_url": "http://localhost:5001",
        "port": 5002,
        "endpoints_documented": 25
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("DOCS_PORT", 5002))
    print(f"Starting Swagger UI Documentation Server on http://localhost:{port}/docs/ ...")
    print(f"Documenting Target API on http://localhost:5001")
    app.run(host="0.0.0.0", port=port, debug=False)
