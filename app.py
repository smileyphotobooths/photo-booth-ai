import os
import openai
import base64
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Your 5 direct .jpg reference images
reference_images = [
    "https://photos.smugmug.com/19225630/i-XXfLj6C/0/NNsqJBNdGXcbGq3TbcR96tctRT6m6JqDgmX4Rt9f4/X3/unknown-X3.jpg",
    "https://photos.smugmug.com/19371714/i-CSb27qT/0/KLDF5vDrXCZcBMNVGgptfc94QK2kNG5KqQBX8qhD3/X3/unknown-X3.jpg",
    "https://photos.smugmug.com/19380336/i-v83k7ks/0/NZN4JPxCgvtdxqGWNBh36F8J2RWmvZhL3dzkz2JbT/X3/unknown-X3.jpg",
    "https://photos.smugmug.com/19535734/i-dmxckL4/0/NWRQJZtrnWkXfVQXrBVwK3vs26Rr6z7csHbTJf3hZ/X3/unknown-X3.jpg",
    "https://photos.smugmug.com/19599994/i-3sPSS2K/0/Kf6Zfbf5rrzHKCjpbKtd4XcPNqKZ8hS3r28p2BRhb/X3/unknown-X3.jpg"
]

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

        # Save uploaded test photo temporarily
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            file_path = tmp.name
            image_file.save(file_path)

        # Build GPT-4 Vision prompt
        vision_prompt = []

        # 1. Attach visual references
        for url in reference_images:
            vision_prompt.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        # 2. Explain Jeremy’s preferred style
        vision_prompt.append({
            "type": "text",
            "text": (
                "These are approved examples of Jeremy’s preferred photo booth style. "
                "He likes crisp, vibrant, bright exposures that flatter skin tones — even slightly overexposed is acceptable. "
                "Avoid images that appear dark, flat, or muddy. These reference photos are the baseline."
            )
        })

        # 3. Attach the current test image
        vision_prompt.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image(file_path)}"}
        })

        # 4. Exposure evaluation instructions
        vision_prompt.append({
            "type": "text",
            "text": (
                f"Here are the current camera settings:\n{metadata}\n\n"
                "Evaluate the test image using the reference examples.\n"
                "Start your reply with one of these emojis:\n"
                "✅ if the photo matches Jeremy’s preferred style\n"
                "🌙 if it’s slightly underexposed\n"
                "☀️ if it’s slightly overexposed\n"
                "⚠️ if it is far off\n\n"
                "If adjustments are needed:\n"
                "- ✅ Keep shutter speed at 1/125 unless absolutely necessary\n"
                "- 🔧 Prioritize adjusting aperture (Av) first\n"
                "- 🔧 Adjust ISO second if needed\n"
                "- ❌ Only suggest changing shutter speed if no other option exists\n\n"
                "Provide specific suggested values (e.g., 'Try f/5.6 or ISO 1600'). "
                "Keep feedback short — no more than 2 concise sentences."
            )
        })

        # Submit request to OpenAI
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": vision_prompt}],
            max_tokens=150
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
