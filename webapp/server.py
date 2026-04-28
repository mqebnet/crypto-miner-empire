@app.route("/admin-cme-secure")
def admin_panel():
    return send_file("static/admin.html")