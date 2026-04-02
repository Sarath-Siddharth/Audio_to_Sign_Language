from flask import Flask, request, jsonify, send_from_directory, render_template
import whisper
import os
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips


os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

app = Flask(__name__)

#Paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

#Whisper model (loads once at startup)
print("Loading Whisper model…")
model = whisper.load_model("base")
print("Whisper ready.")

#Sign dictionary
SIGN_DICT = {
    "1": "1.mp4", "2": "2.mp4", "3": "3.mp4",
    "4": "4.mp4", "5": "5.mp4", "8": "8.mp4",
    "a": "a.mp4", "b": "b.mp4", "c": "c.mp4", "d": "d.mp4",
    "e": "e.mp4", "f": "f.mp4", "g": "g.mp4", "h": "h.mp4",
    "i": "i.mp4", "j": "j.mp4", "k": "k.mp4", "l": "l.mp4",
    "m": "m.mp4", "n": "n.mp4", "o": "o.mp4", "p": "p.mp4",
    "q": "q.mp4", "r": "r.mp4", "s": "s.mp4", "t": "t.mp4",
    "u": "U.mp4", "v": "V.mp4", "w": "w.mp4", "x": "x.mp4",
    "y": "y.mp4", "z": "z.mp4",
    "before": "before.mp4", "big": "big.mp4", "bird": "bird.mp4",
    "blood": "blood.mp4", "book": "book.mp4",
    "bye": "Bye.mp4", "come": "Come.mp4", "four": "four.mp4",
    "go": "go.mp4", "good": "Good.mp4", "good bye": "good bye.mp4",
    "hear": "hear.mp4", "hello": "hello.mp4", "hi": "Hi.mp4",
    "how": "how.mp4", "it": "it.mp4", "me": "Me.mp4",
    "my": "My.mp4", "name": "Name.mp4", "no": "no.mp4",
    "not": "not.mp4", "now": "now.mp4", "one": "one.mp4",
    "our": "our.mp4", "please": "please.mp4", "she": "she.mp4",
    "sign": "Sign.mp4", "super": "super.mp4",
    "thank": "ThankYou.mp4", "thanks": "Thanks.mp4",
    "thank you": "ThankYou.mp4",
    "that": "that.mp4", "they": "they.mp4", "this": "this.mp4",
    "three": "three.mp4", "two": "two.mp4", "type": "Type.mp4",
    "us": "us.mp4", "we": "we.mp4", "welcome": "Welcome.mp4",
    "what": "what.mp4", "when": "when.mp4", "will": "will.mp4",
    "yes": "yes.mp4", "you": "You.mp4", "your": "your.mp4",
}

#Helper: clean a single word token
def clean_word(w):
    return w.strip('.,!?;:"\'()[]{}').lower()

#Helper: map transcript → list of matched sign entries
def text_to_signs(text):
    words = text.strip().split()
    signs = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            phrase = clean_word(words[i]) + " " + clean_word(words[i + 1])
            if phrase in SIGN_DICT:
                signs.append({"word": phrase, "file": SIGN_DICT[phrase]})
                i += 2
                continue
        w = clean_word(words[i])
        if w in SIGN_DICT:
            signs.append({"word": w, "file": SIGN_DICT[w]})
        i += 1
    return signs

#Helper: merge clips into one video
def merge_clips(file_names):
    paths = [os.path.join(ASSETS_DIR, f) for f in file_names]
    print("Looking for files:", paths)  #add this
    paths = [p for p in paths if os.path.isfile(p)]
    print("Found files:", paths)        #and this
    if not paths:
        return None
    clips = [VideoFileClip(p) for p in paths]
    merged = concatenate_videoclips(clips)
    out_path = os.path.join(OUTPUT_DIR, "final.mp4")
    merged.write_videofile(out_path, codec="libx264", audio_codec="aac", logger=None)
    for c in clips:
        c.close()
    merged.close()
    return out_path

#Routes

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    print("Audio received:", audio_file.filename)

    # Save uploaded audio to a temp file
    suffix = os.path.splitext(audio_file.filename)[-1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Transcribe
        print("Transcribing from:", tmp_path)
        result = model.transcribe(tmp_path)
        transcript = result["text"].strip()
        print("Transcript:", transcript)

        # Map to signs
        signs = text_to_signs(transcript)
        print("Signs found:", signs)

        if not signs:
            return jsonify({
                "transcript": transcript,
                "signs": [],
                "total": 0,
                "merged_url": None,
            })

        # Merge clips
        print("Merging clips for:", [s["file"] for s in signs])
        merged_path = merge_clips([s["file"] for s in signs])
        merged_url = "/output/final.mp4" if merged_path else None
        print("Merged path:", merged_path)

        return jsonify({
            "transcript": transcript,
            "signs": signs,
            "total": len(signs),
            "merged_url": merged_url,
        })

    except Exception as e:
        import traceback
        print("ERROR:", traceback.format_exc())  # full error in terminal
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)
# Serve the merged video
@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)

# Serve individual asset clips (for queue preview if needed)
@app.route("/assets/<path:filename>")
def serve_asset(filename):
    return send_from_directory(ASSETS_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
