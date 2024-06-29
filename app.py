import os
from flask import Flask, flash, request, redirect, url_for, send_from_directory, render_template
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__, static_url_path="/assets", static_folder="assets")
app.config['UPLOAD_FOLDER'] = "assets/uploads"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000


@app.route('/')
def home():

    stickers = os.listdir(app.config["UPLOAD_FOLDER"])
    stickers = [s for s in stickers if s[0] != "."]

    return render_template(
        "index.html",
        stickers=stickers,
    )


@app.route('/uploads', methods=['POST'])
def upload_file():

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # check if the post request has the file part
    if 'file' not in request.files:
        print('No file part')
        return redirect(request.url)
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        print("No selected file")
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(path):
            return "Il existe déjà un fichier avec ce nom"
        file.save(path)
        processing = request.form["processing"]
        os.system(f"bash scripts/convert.sh '{path}' '{processing}'")
        return redirect(url_for('home'))


@app.route('/print/<name>')
def print(name):
    name = secure_filename(name)
    path = os.path.join(app.config['UPLOAD_FOLDER'], name)
    os.system(f"bash scripts/print.sh '{path}'")
    return redirect(url_for('home'))


@app.route('/delete/<name>')
def delete(name):
    name = secure_filename(name)
    path = os.path.join(app.config['UPLOAD_FOLDER'], name)
    os.unlink(path)
    return redirect(url_for('home'))
