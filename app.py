import os
import openai
import base64
import tempfile
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Reference images with neutral backgrounds
reference_images = [
    "https://photos.smugmug.com/Images/i-6xxqhhB/0/MNLcnzhPMr7GMVFpGdSqDM7g2HgWWGB6LCzdphBWt/X3/unknown%20%2812%29-X3.jpg",
    "https://photos.smugmug.com/Images/i-hKhXvLf/0/KP4gnRTkWxJ2NqLBkBFHvF6J2H2bRBDQSkzxgXbJ6/X3/unknown%20%2813%29-X3.jpg",
    "https://photos.smugmug.com/Images/i-b9sBzP9/0/NW2WfF2WbzwqFw98QhV2Rz6CZ2jGt4tMZGNQSpC7K/X3/unknown%20%2814%29-X3.jpg"
]

def remove_background(image_path):
    api_key = os.getenv("REMOVEBG_API_KEY")
    with open(image_path, 'rb') as img:
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': img},
            data={'size': 'auto', 'bg_color': 'f5f5f5'},
            headers={'X-Api-Key': api_key}
        )
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as out:
            out.write(response.content)
            return out.name
    else:
        raise Exception(f"remove.bg failed: {response.status_code} - {response.text}")

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

        # Save original
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            original_path = tmp.name
            image_file.save(original_path)

        # Remove background
        cleaned_path = remove_background(original_path)

        # Build GPT Vision prompt
        vision_prompt = []

        # Step 1: Reference images
        for url in reference_images:
            vision_prompt.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        # Step 2: Instruction block
        vision_prompt.append({
            "type": "text",
            "text": (
                "These reference images show Jeremy’s ideal photo booth exposure style. "
                "Focus on the subject’s skin tones, brightness, and clarity. "
                "Ignore the backdrop, sequins, or material."
            )
        })

        # Step 3: User test image
        vision_prompt.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image(cleaned_path)}"}
        })

        # Step 4: Final prompt
        vision_prompt.append({
            "type": "text",
            "text": (
                f"Current camera settings: {metadata}\n\n"
                "Jeremy prefers images that are bright, clean, and vibrant — even if they are slightly overexposed. "
                "If the test image appears even slightly darker than the reference examples, recommend brightening. "
                "Be stricter about underexposure than overexposure.\n\n"

                "Jeremy's usual settings are: ISO 800, f/7.1, 1/125s. Most photos fall within 1 stop of these values. "
                "Use this as the baseline when making suggestions.\n\n"

                "Start your answer with one of these emojis:\n"
                "✅ = exposure is very close to Jeremy’s style — bright and vibrant skin tones\n"
                "🌙 = slightly underexposed — not bad, but needs brightening\n"
                "☀️ = slightly overexposed — still usable\n"
                "⚠️ = far off — fix exposure immediately\n\n"

                "Compare only the subject’s exposure to the reference examples. "
                "If skin tones are darker, duller, or less vibrant than the references, recommend brightening — even if it’s subtle.\n\n"

                "✅ Suggest small, clear adjustments. "
                "Never recommend ISO above 800. Do not adjust Av or ISO more than 1 stop unless absolutely necessary. "
                "Keep shutter speed fixed at 1/125 unless the image is unusably exposed.\n\n"

                "Stay consistent with past responses. If this looks similar to something you already approved, say so. "
                "Keep your answer short — no more than 2 sentences."
            )
        })

        # GPT-4 Vision call
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
        if 'original_path' in locals() and os.path.exists(original_path):
            os.remove(original_path)
        if 'cleaned_path' in locals() and os.path.exists(cleaned_path):
            os.remove(cleaned_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
