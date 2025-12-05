import os
from pathlib import Path
from flask import Flask, flash, request, redirect, url_for, send_from_directory, render_template
from werkzeug.utils import secure_filename

PRINTER = "/dev/usb/lp0"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__, static_url_path="/assets", static_folder="assets")
app.config['UPLOAD_FOLDER'] = "assets/uploads"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000


@app.route('/')
@app.route('/collection/<collection>')
@app.route('/collection/<collection>/<subcol>')
@app.route('/collection/<collection>/<subcol>/<subsubcol>')
def home(collection=None, subcol=None, subsubcol=None):

    if not collection:
        collection = ""
        folder = Path(app.config["UPLOAD_FOLDER"])
    else:
        if subcol:
            collection += "/" + subcol
        if subsubcol:
            collection += "/" + subsubcol
        assert ".." not in collection and "'" not in collection and ";" not in collection
        folder = Path(app.config["UPLOAD_FOLDER"]) / collection

    collections = sorted([collection + "/" + str(s.name) for s in folder.iterdir() if s.is_dir()])
    collections = [c.strip("/") for c in collections]

    stickers = [s for s in folder.iterdir() if s.is_file()]
    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [collection + "/" + str(s.name) for s in stickers]
    stickers = [s.strip("/") for s in stickers]
    print(stickers)

    return render_template(
        "index.html",
        current_collection=collection,
        collections=collections,
        stickers=stickers,
        is_root_collection=not bool(collection),
        printer_is_online=os.path.exists(PRINTER)
    )


@app.route('/stickers', methods=['POST'])
def sticker_upload():

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # check if the post request has the file part
    if 'file' not in request.files:
        print('No file part')
        return redirect(request.url)

    collection = request.form.get('collection')
    if collection != "":
        assert collection and ".." not in collection and "'" not in collection and ";" not in collection
        collection_path = app.config['UPLOAD_FOLDER'] + "/" + collection
        assert Path(collection_path).exists()
    else:
        collection_path = app.config['UPLOAD_FOLDER']

    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        print("No selected file")
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(collection_path, filename)
        if os.path.exists(path):
            return "Il existe déjà un fichier avec ce nom"
        file.save(path)
        return redirect(url_for('home', collection=collection or None))

@app.route('/stickers/print', methods=['POST'])
def sticker_print():
    name = request.args.get("sticker")
    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config['UPLOAD_FOLDER'] + "/" + name
    assert Path(path).exists()
    os.system(f"SIZE=big DITHERING=true bash scripts/print.sh '{path}'")
    return redirect(url_for('home'))

@app.route('/collection/<collection>/print_all', methods=['GET', 'POST'])
def sticker_print_all(collection=None, subcol=None, subsubcol=None):
    if not collection:
        collection = ""
        folder = Path(app.config["UPLOAD_FOLDER"])
    else:
        if subcol:
            collection += "/" + subcol
        if subsubcol:
            collection += "/" + subsubcol
        assert ".." not in collection and "'" not in collection and ";" not in collection
        folder = Path(app.config["UPLOAD_FOLDER"]) / collection

    collections = sorted([collection + "/" + str(s.name) for s in folder.iterdir() if s.is_dir()])
    collections = [c.strip("/") for c in collections]

    stickers = [s for s in folder.iterdir() if s.is_file()]
    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [collection + "/" + str(s.name) for s in stickers]

    for name in stickers:
        assert name and ".." not in name and "'" not in name and ";" not in name
        path = app.config['UPLOAD_FOLDER'] + '/' + name
        print(path)
        assert Path(path).exists()
        os.system(f"SIZE=big DITHERING=true bash scripts/print.sh '{path}'")

    return redirect(url_for('home'))

@app.route('/stickers/delete', methods=['DELETE'])
def sticker_delete():
    name = request.args.get("sticker")
    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config['UPLOAD_FOLDER'] + "/" + name
    assert Path(path).exists()
    os.unlink(path)
    return redirect(url_for('home'))


@app.route('/stickers/search')
def search():

    pattern = request.args.get('q')
    assert pattern.lower().replace(" ", "").replace("_", "").isalnum(), ""

    matches = [f for f in list(Path(app.config["UPLOAD_FOLDER"]).rglob("*")) if f.is_file() and pattern in str(f)]

    stickers = sorted(matches, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [str(s).replace(app.config["UPLOAD_FOLDER"], "") for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    return render_template(
        "index.html",
        current_collection="",
        collections=[],
        stickers=stickers,
        is_root_collection=False,
        printer_is_online=os.path.exists(PRINTER)
    )
