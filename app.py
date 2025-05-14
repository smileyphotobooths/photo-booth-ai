import os
import openai
import base64
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Updated direct .jpg reference images
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

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            file_path = tmp.name
            image_file.save(file_path)

        vision_prompt = []

        # Reference images
        for url in reference_images:
            vision_prompt.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        # What these references mean
        vision_prompt.append({
            "type": "text",
            "text": (
                "These are approved photos from Jeremy’s photo booth. Use them as reference for brightness, clarity, and skin tone exposure. "
                "Match this style visually — don't assume preferences."
            )
        })

        # Test photo
        vision_prompt.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image(file_path)}"}
        })

        # Final instruction
        vision_prompt.append({
            "type": "text",
            "text": (
                f"Current camera settings: {metadata}\n\n"
                "Start your reply with one of these emojis:\n"
                "✅ = matches reference style\n"
                "🌙 = slightly underexposed\n"
                "☀️ = slightly overexposed\n"
                "⚠️ = far off\n\n"
                "If changes are needed, suggest **specific values**. "
                "Keep Tv at 1/125 unless the photo is extremely off. Prioritize adjusting aperture (Av) first, then ISO only if absolutely needed. "
                "Do not recommend changes just to make a suggestion. If this test shot already matches the references — stop and confirm it.\n\n"
                "If skin tones already approach RGB 240+, do not suggest brightening. "
                "Only recommend changes when they would clearly move the image closer to Jeremy’s approved examples. "
                "Keep response very short — 1 sentence."
            )
        })

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
