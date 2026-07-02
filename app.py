import os
import base64
from pathlib import Path
from io import BytesIO

import blurhash
from PIL import Image, ImageEnhance
from flask import Flask, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename
from persist_cache import cache


PRINTER = "/dev/usb/lp0"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


class Sticker:
    path: str | os.PathLike
    blurhash: str
    width: int
    height: int

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)

        upload_folder = Path("assets/uploads")
        try:
            self.relative = str(self.path.relative_to(upload_folder))
        except ValueError:
            self.relative = str(self.path)

        self.width, self.height, self.blurhash = get_sticker_meta(self.path)

    def __repr__(self):
        return f"path: <{self.path}> size:<{self.width}x{self.height}> hash:<{self.blurhash}>"


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

    sticker_objects = [Sticker(Path(app.config['UPLOAD_FOLDER']) / s) for s in stickers]

    return render_template(
        "index.html",
        current_collection=collection,
        collections=collections,
        stickers=sticker_objects,
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
    else:
        return "Ohno, le fichier n'est pas ok!"


@app.route('/stickers/print', methods=['POST'])
def sticker_print():

    name = request.args.get("sticker")
    quantity = request.args.get("quantity", 1)
    quantity = int(quantity)
    size = request.args.get("size", "default")
    dithering = request.args.get("dithering", "true")

    assert quantity > 0 and quantity < 500
    assert size in ["default", "large", "small"]
    assert dithering in ["true", "false"]

    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config['UPLOAD_FOLDER'] + "/" + name
    assert Path(path).exists()
    ret = os.system(f"SIZE={size} DITHERING={dithering} QUANTITY={quantity} bash scripts/print.sh '{path}'")
    return jsonify(success=ret == 0)


@app.route('/stickers/<collection>/<subcol>/<subsubcol>/print_all', methods=['GET', 'POST'])
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

    any_failed = False
    for name in stickers:
        assert name and ".." not in name and "'" not in name and ";" not in name
        path = app.config['UPLOAD_FOLDER'] + '/' + name
        assert Path(path).exists()
        ret = os.system(f"bash scripts/print.sh '{path}'")
        if ret != 0:
            any_failed = True

    return jsonify(success=any_failed is False)


@app.route('/stickers/delete', methods=['DELETE'])
def sticker_delete():
    name = request.args.get("sticker")
    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config['UPLOAD_FOLDER'] + "/" + name
    assert Path(path).exists()
    os.unlink(path)
    return '', 204


@app.route('/stickers/search')
def search():

    pattern = request.args.get('q')
    assert pattern.lower().replace(" ", "").replace("_", "").isalnum(), ""

    matches = [f for f in list(Path(app.config["UPLOAD_FOLDER"]).rglob("*")) if f.is_file() and pattern in str(f)]

    stickers = sorted(matches, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [str(s).replace(app.config["UPLOAD_FOLDER"], "") for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    sticker_objects = [Sticker(Path(app.config['UPLOAD_FOLDER']) / s) for s in stickers]

    return render_template(
        "index.html",
        current_collection="",
        collections=[],
        stickers=sticker_objects,
        is_root_collection=False,
        printer_is_online=os.path.exists(PRINTER)
    )


@app.route('/stickers/process', methods=['GET', 'POST'])
def sticker_process():

    name = request.args.get("sticker")
    brightness = float(request.args.get("brightness"))
    contrast = float(request.args.get("contrast"))
    brightness2 = float(request.args.get("brightness2"))

    assert brightness >= 0 and brightness <= 5
    assert contrast >= 0 and contrast <= 5
    assert brightness2 >= 0 and brightness2 <= 5
    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config['UPLOAD_FOLDER'] + "/" + name
    assert Path(path).exists()

    with Image.open(path) as im:
        if im.mode != 'L':
            im = im.convert('L')
        im = ImageEnhance.Brightness(im).enhance(brightness)
        im = ImageEnhance.Brightness(im).enhance(contrast)
        im = ImageEnhance.Brightness(im).enhance(brightness2)

        if request.method == 'POST':
            path_without_ext, ext = path.rsplit(".", 1)
            new_name = f"{path_without_ext}_bw_b{brightness}c{contrast}b2{brightness2}.{ext}"
            im.save(new_name, format=ext.upper())
            return ""
        else:
            buffer = BytesIO()
            im.save(buffer, format="JPEG")
            img_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
            return img_base64


@cache(name="sticker_meta", dir=".cache")
def get_sticker_meta(file_path: str | os.PathLike) -> tuple[int, int, str]:
    """Return (width, height, blurhash) of the image"""
    with Image.open(file_path) as im:
        width, height = im.size
        im.thumbnail((32, 32))
        bh = blurhash.encode(im, x_components=4, y_components=3)

    return (width, height, bh)

