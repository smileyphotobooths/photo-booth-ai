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
This is an event photo booth. Bright, crisp, vibrant images are preferred even if it risks minor overexposure. The shutter speed is fixed at 1/125. Flash was used.

The previous photo had settings:
{previous}

You suggested those settings.

Here are the new camera settings and the resulting test photo:
{metadata}

Evaluate whether exposure improved or worsened. Give a simple, clear suggestion (1–2 sentences max) to better match the preferred photo booth style. Prioritize adjusting aperture (Av), then ISO. Only change shutter speed as a last resort.
"""
        else:
            prompt = f"""
This is an event photo booth. Bright, crisp, vibrant images are preferred even if it risks minor overexposure. The shutter speed is fixed at 1/125. Flash was used.

Here are the current camera settings and test photo:
{metadata}

Give a short and clear exposure assessment. Recommend any changes needed to match the preferred bright, flattering style. Favor aperture (Av), then ISO. Avoid changing shutter speed unless absolutely necessary. Keep the response under 2 sentences.
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
