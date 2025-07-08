import os
from flask import Flask, render_template, request
from mindee import Client
from mindee.product import ResumeV1

app = Flask(__name__)

# Initialize Mindee client
mindee_client = Client(api_key="40602753ca8c143888e4131353abc30c")

# Helper function to safely extract .value or fallback to string
def extract_value(item):
    return item.value if hasattr(item, 'value') else str(item)

# Helper function to join lists of Mindee objects
def extract_list(items):
    return ", ".join([extract_value(i) for i in items]) if items else ""

@app.route("/")
def index():
    print("[DEBUG] Rendering index.html...")
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    print("[DEBUG] Upload route triggered.")

    if "resume" not in request.files:
        print("[ERROR] No file part in the request.")
        return "No file uploaded", 400

    file = request.files["resume"]

    if file.filename == "":
        print("[ERROR] Empty filename submitted.")
        return "No file selected", 400

    os.makedirs("temp_resume", exist_ok=True)
    filepath = os.path.join("temp_resume", file.filename)
    file.save(filepath)
    print(f"[DEBUG] Resume saved at {filepath}")

    try:
        print("[DEBUG] Sending file to Mindee API for parsing...")
        input_doc = mindee_client.source_from_path(filepath)
        result = mindee_client.enqueue_and_parse(ResumeV1, input_doc)
        doc = result.document
        prediction = doc.inference.prediction

        print("[DEBUG] Parsing successful.")

        # Extract full name from given_names + surname
        given_names = [extract_value(n) for n in getattr(prediction, "given_names", [])]
        surname = extract_value(getattr(prediction, "surname", ""))

        full_name = " ".join(given_names + [surname]).strip()

        # Extract other fields safely
        email = extract_value(prediction.emails[0]) if getattr(prediction, "emails", []) else ""
        phone = extract_value(prediction.phone_numbers[0]) if getattr(prediction, "phone_numbers", []) else ""
        languages = extract_list(getattr(prediction, "languages", []))
        skills = extract_list(getattr(prediction, "skills", []))

        # Extract experience
        experience = "\n".join([
            f"{extract_value(e.title)} at {extract_value(e.company)}"
            for e in getattr(prediction, "experiences", [])
            if getattr(e, "title", None) and getattr(e, "company", None)
        ])

        # Extract education
        education = "\n".join([
            extract_value(e.school)
            for e in getattr(prediction, "education", [])
            if getattr(e, "school", None)
        ])

        # Store data for result.html
        resume_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "languages": languages,
            "skills": skills,
            "experience": experience,
            "education": education
        }

        # Debug print all fields
        for key, value in resume_data.items():
            print(f"[{key.upper()}] → {value}")

        return render_template("result.html", resume=resume_data)

    except Exception as e:
        print(f"[ERROR] An error occurred while parsing the resume: {e}")
        return "An error occurred while parsing the resume.", 500

if __name__ == "__main__":
    print("[INFO] Starting Flask app on http://127.0.0.1:5000")
    app.run(debug=True)
