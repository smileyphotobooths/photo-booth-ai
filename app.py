import os
import openai
import base64
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Your 5 reference images from SmugMug
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

        # Build the multi-part prompt for GPT-4 Vision
        vision_prompt = []

        # Reference section
        for url in reference_images:
            vision_prompt.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        vision_prompt.append({
            "type": "text",
            "text": (
                "These 5 images are approved examples of Jeremy's preferred photo booth style. "
                "He likes bright, crisp, vibrant images with clean skin tones and flattering lighting — even if they are slightly overexposed. "
                "Avoid underexposed or muted results. Use these reference images to evaluate the test photo's exposure."
            )
        })

        # Test photo section
        vision_prompt.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image(file_path)}"}
        })

        vision_prompt.append({
            "type": "text",
            "text": (
                f"Here are the current camera settings:\n{metadata}\n\n"
                "Compare this test photo to the reference examples. Start your reply with one of these emojis:\n"
                "✅ if the photo matches Jeremy’s preferred style,\n"
                "🌙 if it's slightly underexposed,\n"
                "☀️ if it's slightly overexposed,\n"
                "⚠️ if it is clearly off.\n\n"
                "Keep your response to 1 sentence. Suggest exposure adjustments only if it improves alignment with Jeremy’s style. "
                "Favor brightness when unsure."
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
