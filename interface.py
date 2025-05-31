# /sz/src/interface.py

"""
Module: interface.py
Purpose: Serve local web UI for live status, override control, log access.
Consumes:
- CONFIG.ui_host, CONFIG.ui_port
- CONFIG.override_file, CONFIG.log_dir
Provides:
- /live: current readings and decision
- /override: set override mode
- /logs: download data.csv or decisions.csv
Behavior:
- Fully offline Flask server
- No JavaScript required to operate
- Designed for non-technical users
"""

from flask import Flask, request, send_file, render_template_string
from config_loader import CONFIG
from sensor_reader import read_sensors
from override_manager import get_override_mode
from decision_engine import decide_hvac_action

app = Flask(__name__)

LIVE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>SentientZone Status</title></head>
<body>
<h2>Live Status</h2>
<table border="1">
<tr><th>Temperature</th><td>{{ temp }} °C</td></tr>
<tr><th>Humidity</th><td>{{ humid }} %</td></tr>
<tr><th>Motion</th><td>{{ motion }}</td></tr>
<tr><th>Status</th><td>{{ status }}</td></tr>
<tr><th>Override</th><td>{{ override }}</td></tr>
<tr><th>HVAC State</th><td>{{ state }}</td></tr>
<tr><th>Mode</th><td>{{ mode }}</td></tr>
<tr><th>Cause</th><td>{{ cause }}</td></tr>
</table>
<p><a href="/override?mode=manual_on">Manual On</a> |
<a href="/override?mode=manual_off">Manual Off</a> |
<a href="/override?mode=auto">Auto</a></p>
<p><a href="/logs?type=data">Download Data Log</a> |
<a href="/logs?type=decisions">Download Decisions Log</a></p>
</body>
</html>
"""

@app.route("/live")
def live():
    sensor = read_sensors()
    override = get_override_mode()
    decision = decide_hvac_action(sensor, override)

    return render_template_string(LIVE_TEMPLATE,
        temp=sensor["temperature"],
        humid=sensor["humidity"],
        motion=sensor["motion"],
        status=sensor["status"],
        override=override,
        state=decision["hvac_state"],
        mode=decision["mode"],
        cause=decision["cause"]
    )

@app.route("/override")
def override():
    mode = request.args.get("mode", "").lower()
    if mode in ("manual_on", "manual_off", "auto"):
        with open(CONFIG.override_file, "w") as f:
            f.write(mode)
    return "<p>Override set to: {}</p><p><a href='/live'>Back</a></p>".format(mode)

@app.route("/logs")
def logs():
    log_type = request.args.get("type")
    if log_type == "data":
        return send_file(CONFIG.log_dir / "data.csv", as_attachment=True)
    elif log_type == "decisions":
        return send_file(CONFIG.log_dir / "decisions.csv", as_attachment=True)
    return "<p>Invalid log type. Use ?type=data or ?type=decisions</p>"

def start_interface():
    app.run(host=CONFIG.ui_host, port=CONFIG.ui_port)
