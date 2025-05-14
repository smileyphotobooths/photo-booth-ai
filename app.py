import os
import openai
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import tempfile

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/analyze', methods=['POST'])
def analyze():
    image_file = request.files.get('file')
    metadata = request.form.get('metadata')

    if not image_file or not metadata:
        return jsonify({"error": "Missing image or metadata"}), 400

    # Save image temporarily
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        file_path = tmp.name
        image_file.save(file_path)

    try:
        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"This is a photo taken in a photo booth setup. The camera settings are: {metadata}. Evaluate the exposure and lighting. Is it underexposed, overexposed, or just right? Suggest any changes to ISO, aperture (Av), or shutter speed (Tv) if needed. Flash was used.",
                        },
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

        suggestion = response.choices[0].message.content
        return jsonify({"suggestion": suggestion})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(file_path)

def base64_image(path):
    import base64
    with open(path, "rb") as img:
        return base64.b64encode(img.read()).decode("utf-8")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
