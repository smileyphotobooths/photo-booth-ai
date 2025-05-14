import os
import openai
import base64
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

def base64_image(path):
    with open(path, "rb") as img:
        return base64.b64encode(img.read()).decode("utf-8")

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        image_file = request.files.get('file')
        metadata = request.form.get('metadata')
        previous = request.form.get('previous_settings')

        if not image_file or not metadata:
            return jsonify({"error": "Missing image or metadata"}), 400

        # Save image temporarily
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            file_path = tmp.name
            image_file.save(file_path)

        # Prepare prompt message
        if previous:
            prompt = f"""
You are an AI exposure assistant helping a photo booth technician. Shutter speed is fixed at 1/125. The flash was used.

The previous photo had settings:
{previous}

You suggested those settings.

Here are the new settings and the resulting test photo:
{metadata}

Evaluate whether exposure improved or worsened. Give a simple, clear suggestion. Prioritize adjusting aperture (Av), then ISO. Only change shutter speed as a last resort. Keep response under 2 sentences.
"""
        else:
            prompt = f"""
You are an AI exposure assistant helping a photo booth technician. Shutter speed is fixed at 1/125. The flash was used.

Here are the camera settings and test photo:
{metadata}

Give a short and clear exposure assessment. If changes are needed, prioritize adjusting aperture (Av), then ISO. Avoid changing shutter speed unless absolutely necessary. Keep response under 2 sentences.
"""

        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image(file_path)}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=200
        )

        suggestion = response.choices[0].message.content.strip()
        return jsonify({"suggestion": suggestion})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
