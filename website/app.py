from flask import Flask, render_template
from auth import auth_bp

app = Flask("Google Login App")
app.secret_key = "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"  

app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)