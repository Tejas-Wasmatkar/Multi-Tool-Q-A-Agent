import json
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from agent import run_agent

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    pdf_text     = None
    pdf_filename = None

    if "pdf" in request.files:
        pdf_file = request.files["pdf"]
        if pdf_file.filename:
            pdf_bytes    = pdf_file.read()
            doc          = fitz.open(stream=pdf_bytes, filetype="pdf")
            pdf_text     = "\n".join(page.get_text() for page in doc)
            pdf_filename = pdf_file.filename

    def generate():
        try:
            for event_type, payload in run_agent(question, pdf_text, pdf_filename):
                yield f"data: {json.dumps({'type': event_type, 'payload': payload})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)