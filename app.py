import re
import sys
import subprocess
import os
import base64
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path
from io import BytesIO
from slugify import slugify
import numpy as np
from markupsafe import Markup
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from flask import Flask, request, redirect, render_template, jsonify
from werkzeug.utils import secure_filename
from persist_cache import cache

load_dotenv()
PRINTER = os.getenv("PRINTER") or "/dev/usb/lp0"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


class Sticker:
    path: str | os.PathLike
    width: int
    height: int

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)

        upload_folder = Path("assets/uploads")
        try:
            self.relative = str(self.path.relative_to(upload_folder))
        except ValueError:
            self.relative = str(self.path)

        self.width, self.height = get_sticker_meta(self.path)

    def __repr__(self):
        return f"path: <{self.path}> size:<{self.width}x{self.height}>"


app = Flask(__name__, static_url_path="/assets", static_folder="assets")
app.config["UPLOAD_FOLDER"] = "assets/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000


@app.route("/")
@app.route("/collection/<collection>")
@app.route("/collection/<collection>/<subcol>")
@app.route("/collection/<collection>/<subcol>/<subsubcol>")
def home(collection=None, subcol=None, subsubcol=None):

    if not collection:
        collection = ""
        folder = Path(app.config["UPLOAD_FOLDER"])
    else:
        if subcol:
            collection += "/" + subcol
        if subsubcol:
            collection += "/" + subsubcol
        assert (
            ".." not in collection and "'" not in collection and ";" not in collection
        )
        folder = Path(app.config["UPLOAD_FOLDER"]) / collection

    collections = sorted(
        [collection + "/" + str(s.name) for s in folder.iterdir() if s.is_dir()]
    )
    collections = [c.strip("/") for c in collections]

    stickers = [s for s in folder.iterdir() if s.is_file()]
    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [collection + "/" + str(s.name) for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    sticker_objects = [Sticker(Path(app.config["UPLOAD_FOLDER"]) / s) for s in stickers]

    return render_template(
        "index.html",
        current_collection=collection,
        collections=collections,
        stickers=sticker_objects,
        is_root_collection=not bool(collection),
        printer_is_online=os.path.exists(PRINTER),
        fonts=fonts,
    )


@app.route("/stickers", methods=["POST"])
def sticker_upload():

    def allowed_file(filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    # check if the post request has the file part
    if "file" not in request.files:
        print("No file part")
        return redirect(request.url)

    collection = request.form.get("collection")
    if collection != "":
        assert (
            collection
            and ".." not in collection
            and "'" not in collection
            and ";" not in collection
        )
        collection_path = app.config["UPLOAD_FOLDER"] + "/" + collection
        assert Path(collection_path).exists()
    else:
        collection_path = app.config["UPLOAD_FOLDER"]

    file = request.files["file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if not file or not file.filename.strip():
        return "Pas de fichier sélectionné !?", 499
    if not allowed_file(file.filename):
        return "Ohno, cette extension n'est pas autorisée!", 499

    filename = secure_filename(file.filename)
    path = os.path.join(collection_path, filename)
    if os.path.exists(path):
        return "Il existe déjà un fichier avec ce nom", 499
    file.save(path)

    return render_template("sticker.html", sticker=Sticker(path))


@app.route("/stickers/print", methods=["POST"])
def sticker_print():

    if not os.path.exists(PRINTER):
        return "Erreur: l'imprimante est hors ligne / inaccessible !", 400

    try:
        name = request.args.get("sticker")
        quantity = request.form.get("quantity", 1, type=int)
        size = request.form.get("size", "default")
        dithering = request.form.get("dithering", "true")

        assert (
            quantity > 0 and quantity < 500
        ), f"La quantité '{quantity}' est incorrecte"
        assert size in [
            "default",
            "large",
            "small",
        ], f"La taille '{size}' est incorrecte"
        assert dithering in [
            "true",
            "false",
        ], f"'dithering' devrait être 'true' ou 'false, pas '{dithering}'"

        assert (
            name and ".." not in name and "'" not in name and ";" not in name
        ), f"Caractère interdits dans le nom du sticker"
        path = app.config["UPLOAD_FOLDER"] + "/" + name
        assert Path(path).exists(), f"Le fichier '{name}' n'existe pas ?"
    except Exception as e:
        return f"Erreur: {e}", 400

    ret = os.system(
        f"SIZE={size} DITHERING={dithering} QUANTITY={quantity} bash scripts/print.sh '{path}'"
    )
    return (
        ""
        if ret == 0
        else ("Ohno ! L'impression a échoué ! Il faut regarder les logs !", 400)
    )


@app.route(
    "/stickers/<collection>/<subcol>/<subsubcol>/print_all", methods=["GET", "POST"]
)
def sticker_print_all(collection=None, subcol=None, subsubcol=None):
    if not collection:
        collection = ""
        folder = Path(app.config["UPLOAD_FOLDER"])
    else:
        if subcol:
            collection += "/" + subcol
        if subsubcol:
            collection += "/" + subsubcol
        assert (
            ".." not in collection and "'" not in collection and ";" not in collection
        )
        folder = Path(app.config["UPLOAD_FOLDER"]) / collection

    collections = sorted(
        [collection + "/" + str(s.name) for s in folder.iterdir() if s.is_dir()]
    )
    collections = [c.strip("/") for c in collections]

    stickers = [s for s in folder.iterdir() if s.is_file()]
    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [collection + "/" + str(s.name) for s in stickers]

    any_failed = False
    for name in stickers:
        assert name and ".." not in name and "'" not in name and ";" not in name
        path = app.config["UPLOAD_FOLDER"] + "/" + name
        assert Path(path).exists()
        ret = os.system(f"bash scripts/print.sh '{path}'")
        if ret != 0:
            any_failed = True

    return jsonify(success=any_failed is False)


@app.route("/stickers/delete", methods=["DELETE"])
def sticker_delete():
    name = request.args.get("sticker")
    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config["UPLOAD_FOLDER"] + "/" + name
    assert Path(path).exists()
    os.unlink(path)
    return ""


@app.route("/stickers/search")
def search():

    pattern = request.args.get("q")
    assert pattern.lower().replace(" ", "").replace("_", "").isalnum(), ""

    matches = [
        f
        for f in list(Path(app.config["UPLOAD_FOLDER"]).rglob("*"))
        if f.is_file() and pattern in str(f)
    ]

    stickers = sorted(matches, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [str(s).replace(app.config["UPLOAD_FOLDER"], "") for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    sticker_objects = [Sticker(Path(app.config["UPLOAD_FOLDER"]) / s) for s in stickers]

    return render_template(
        "index.html",
        current_collection="",
        collections=[],
        stickers=sticker_objects,
        is_root_collection=False,
        printer_is_online=os.path.exists(PRINTER),
        fonts=fonts,
    )


@app.route("/stickers/massprint")
def sticker_massprint():
    return render_template("massprint.html", sticker=request.args.get("sticker"))


@app.route("/stickers/edit")
def sticker_edit(sticker=None):
    return render_template("edit.html", sticker=request.args.get("sticker"))


@app.route("/stickers/process", methods=["GET", "POST"])
def sticker_process():

    if request.method == "POST":
        name = request.form.get("sticker")
        decolor = request.form.get("decolor", type=float)
        brightness = request.form.get("brightness", type=float)
        contrast = request.form.get("contrast", type=float)
        brightness2 = request.form.get("brightness2", type=float)
    else:
        name = request.args.get("sticker")
        decolor = request.args.get("decolor", type=float)
        brightness = request.args.get("brightness", type=float)
        contrast = request.args.get("contrast", type=float)
        brightness2 = request.args.get("brightness2", type=float)

    assert decolor >= 0 and decolor <= 2
    assert brightness >= 0 and brightness <= 5
    assert contrast >= 0 and contrast <= 5
    assert brightness2 >= 0 and brightness2 <= 5
    assert name and ".." not in name and "'" not in name and ";" not in name
    path = app.config["UPLOAD_FOLDER"] + "/" + name
    assert Path(path).exists()

    with Image.open(path) as im:
        if im.mode != "L":
            im = _decolor_image(im, strength=decolor)

        im = ImageEnhance.Brightness(im).enhance(brightness)
        im = ImageEnhance.Brightness(im).enhance(contrast)
        im = ImageEnhance.Brightness(im).enhance(brightness2)

        if request.method == "POST":
            path_without_ext, ext = path.rsplit(".", 1)
            new_name = f"{path_without_ext}_bw{decolor}_b{brightness}c{contrast}b2{brightness2}.{ext}"
            pil_format = ext.upper()
            if pil_format == "JPG":
                pil_format = "JPEG"
            im.save(new_name, format=pil_format)
            return render_template("sticker.html", sticker=Sticker(new_name))
        else:
            buffer = BytesIO()
            im.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue()).decode()


def _decolor_image(img, strength=1.0, power=2.0):
    # Strength: 0.0 -> 1.0, how strongly colorful pixels are whitened.
    # Power: 1.0 -> 3.0 : hgher values preserve dark colors more.

    img = img.convert("RGB")

    # Float image in [0,1]
    rgb = np.asarray(img, dtype=np.float32) / 255.0

    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    # Perceived grayscale (Rec. 601 luminance)
    lum = 0.3 * r + 0.55 * g + 0.15 * b

    # Chroma (amount of color)
    mx = np.maximum.reduce([r, g, b])
    mn = np.minimum.reduce([r, g, b])
    chroma = mx - mn

    # Effective color strength
    colorfulness = chroma * (mx ** (power - 1))

    # Blend grayscale toward white
    gray = lum + strength * colorfulness * (1.0 - lum)

    # Clamp to [0,1]
    gray = np.clip(gray, 0.0, 1.0)

    out = Image.fromarray((gray * 255).astype(np.uint8), mode="L")
    return out
    # out.save("output.png")


@app.route("/label/generate", methods=["GET", "POST"])
def label_generate():

    text = request.values.get("text")
    font = request.values.get("font")

    assert isinstance(text, str) and len(text) < 10000
    assert isinstance(font, str) and font in fonts

    img = text_to_image(
        text=text,
        font_filepath=f"assets/fonts/{fonts[font]['filename']}",
        font_size=60,
        color=(0, 0, 0),
    )

    if request.method == "POST":

        action = request.values.get("action")
        assert action in ["print", "save"]
        print_size = request.values.get("print-label-size")
        assert print_size in ["small", "large"]

        slug = slugify(text, separator="_", max_length=100)
        if action == "print":
            path = f"/tmp/{slug}.png"
            img.save(path, format="PNG")

            dithering = "true"
            quantity = 1
            ret = os.system(
                f"SIZE={print_size} DITHERING={dithering} QUANTITY={quantity} bash scripts/print.sh '{path}'"
            )
            return "" if ret == 0 else ("Uhoh, l'impression échoué ?!", 500)
        else:
            path = f"assets/uploads/{slug}.png"
            img.save(path, format="PNG")
            return render_template("sticker.html", sticker=Sticker(path))
    else:
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


@cache(name="sticker_meta", dir=".cache")
def get_sticker_meta(file_path: str | os.PathLike) -> tuple[int, int]:
    """Return (width, height) of the image"""
    with Image.open(file_path) as im:
        width, height = im.size
    return (width, height)


def text_to_image(
    text: str,
    font_filepath: str,
    font_size: int,
    color: tuple[int, int, int],
    font_align: str = "center",
):
    font = ImageFont.truetype(font_filepath, size=font_size)

    # Temporary image used only for measuring the text
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)

    left, top, right, bottom = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        align=font_align,
    )

    width = int(right - left)
    height = int(bottom - top)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Offset by the bbox origin in case it isn't (0, 0)
    draw.multiline_text(
        (-left, -top),
        text,
        font=font,
        fill=color,
        align=font_align,
    )

    return img


def list_fonts():
    raw_list = (
        subprocess.getoutput("fc-scan --format '%{file}: %{family}\n' assets/fonts/")
        .strip()
        .split("\n")
    )
    fonts = {}
    for raw_infos in raw_list:
        path, names = raw_infos.split(":")
        filename = path.split("/")[-1].strip()
        name = names.split(",")[-1].strip()
        if name in fonts:
            print(
                f"Uhoh, duplicate font with name '{name}' ? ({fonts[name]['filename']} vs {filename})",
                file=sys.stderr,
            )
            continue
        fonts[name] = {"filename": filename}
    return fonts


fonts = list_fonts()

def icon(name, attrs={"aria-hidden": "true"}, size="1.25em", classes=[]):
    if not re.fullmatch(r"[a-z:-]+", name):
        raise ValueError(f"Invalid icon name: {name}")

    path = Path(app.static_folder) / "icons" / f"{name}.svg"

    assert os.path.exists(path), f"Icon {path} doesn't exist, maybe you need to re-fetch assets"

    attrs["class"] = ' '.join(["icon"] + classes)
    attrs = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])

    svg = path.read_text(encoding="utf-8")
    svg = re.sub(
        r'width="1em" height="1em"',
        f'width="{size}" height="{size}"',
        svg,
        count=1
    )
    svg = re.sub(
        r"<svg(?=[\s>])",
        "<svg " + attrs,
        svg,
        count=1,
    )

    return Markup(svg)

app.jinja_env.globals["icon"] = icon
