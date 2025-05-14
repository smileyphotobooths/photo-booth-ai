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

        # Prompt with emoji + memory + smart brightness preference
        if previous:
            prompt = f"""
This is an event photo booth. Slightly brighter than standard exposure is preferred, but avoid blown-out highlights or harsh brightness. The image should look vibrant, clean, and flattering. Skin tones should remain natural-looking. Shutter speed is fixed at 1/125. Flash was used.

The previous photo had settings:
{previous}

You suggested those settings.

Here are the new camera settings and the resulting test photo:
{metadata}

Start your response with one of these emojis:
✅ if the image looks great and no changes are needed,  
☀️ if it's slightly overexposed,  
🌙 if slightly underexposed,  
⚠️ if the image is clearly over or underexposed.

Give a short, clear recommendation (1–2 sentences max) to better match this preferred style. Only suggest a change if it would improve the image — and when unsure, lean slightly brighter to match the vibrant photo booth style. But do not keep increasing brightness once the look is achieved. Prioritize adjusting aperture (Av), then ISO. Only change shutter speed if absolutely necessary.
"""
        else:
            prompt = f"""
This is an event photo booth. Slightly brighter than standard exposure is preferred, but avoid blown-out highlights or excessive brightness. Images should appear vibrant and flattering, especially for skin tones. The shutter speed is fixed at 1/125. Flash was used.

Here are the current camera settings and test photo:
{metadata}

Start your response with one of these emojis:
✅ if the image looks great and no changes are needed,  
☀️ if it's slightly overexposed,  
🌙 if slightly underexposed,  
⚠️ if the image is clearly over or underexposed.

Give a short and clear exposure assessment. Recommend changes only if they'd clearly improve the result — and when unsure, lean slightly brighter to match the vibrant photo booth style. Do not continue increasing brightness once the look is achieved. Prioritize aperture (Av), then ISO. Avoid changing shutter speed unless absolutely necessary. Keep the response under 2 sentences.
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
