import re
import sys
import subprocess
import os
import base64
import time
from tempfile import TemporaryDirectory
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
from slugify import slugify
import numpy as np
from markupsafe import Markup
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from flask import Flask, request, redirect, render_template, jsonify
from werkzeug.utils import secure_filename
from persist_cache import cache

load_dotenv()
PRINTER = os.getenv("PRINTER", "/dev/usb/lp0")
PRINTER_MODEL = os.getenv("PRINTER_MODEL", "QL-570")
USE_QUEUE = os.getenv("USE_QUEUE", "false")
DEFAULT_PRINT_SIZE = os.getenv("DEFAULT_PRINT_SIZE", "large")
LABEL = os.getenv("LABEL", "62")
LABEL_IDEAL_PIXEL_SIZE = os.getenv("LABEL_IDEAL_PIXEL_SIZE", "696")
DIDDER_BIN = os.getenv("DIDDER_BIN", "assets/didder_1.3.0_linux_64-bit")
TAGS = os.getenv("TAGS", "").split(",")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def assert_safe_filename(f: str) -> None:
    assert ".." not in f and "'" not in f and ";" not in f, f"Caractères interdits dans le nom de fichier ou dossier « {f} »"

class Sticker:
    path: Path
    width: int
    height: int
    relative: str
    collection: str
    name: str
    tags: list[str]
    authors: list[str]

    def __init__(self, path: str | os.PathLike):

        self.path = Path(path)  # Path() is idempotent, not an issue if path is already a Path()
        relative_to = self.path.relative_to(UPLOAD_FOLDER)
        self.relative = str(relative_to)
        self.collection = str(relative_to.parent)
        raw_name, self.ext = self.path.name.rsplit(".", 1)
        parts = raw_name.split("__")
        self.name = parts[0]
        self.tags = []
        self.authors = []
        for part in parts:
            if part.startswith("#"):
                self.tags.append(part.strip("#"))
            elif part.startswith("@"):
                self.authors.append(part.strip("@"))

        self.width, self.height = Sticker.get_dimensions(self.path)

    def metadata_to_path(self) -> str:

        assert_safe_filename(self.name)
        assert_safe_filename(self.collection)

        parts = (
            [self.name]
            + [f"#{tag}" for tag in self.tags]
            + [f"@{author}" for author in self.authors]
        )
        fullname = "__".join(parts) + "." + self.ext

        return str(UPLOAD_FOLDER / self.collection / fullname)

    @cache(name="sticker_meta", dir=".cache")
    @staticmethod
    def get_dimensions(path: Path) -> tuple[int, int]:
        """Return (width, height) of the image"""
        try:
            with Image.open(path) as im:
                width, height = im.size
        except Exception as e:
            print(f"Failed to check image size for {path}: {e}")
            return (0, 0)
        else:
            return (width, height)

    def __repr__(self):
        return f"path: <{self.path}> size:<{self.width}x{self.height}>"


app = Flask(__name__, static_url_path="/assets", static_folder="assets")
app.config["UPLOAD_FOLDER"] = "assets/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000

UPLOAD_FOLDER = Path(app.config["UPLOAD_FOLDER"]).resolve()


@app.route("/")
@app.route("/collection/<collection>")
@app.route("/collection/<collection>/<subcol>")
@app.route("/collection/<collection>/<subcol>/<subsubcol>")
def home(collection=None, subcol=None, subsubcol=None):

    if not collection:
        collection = ""
        folder = UPLOAD_FOLDER
    else:
        if subcol:
            collection += "/" + subcol
        if subsubcol:
            collection += "/" + subsubcol
        assert_safe_filename(collection)
        folder = UPLOAD_FOLDER / collection

    collections = sorted(
        [collection + "/" + str(s.name) for s in folder.iterdir() if s.is_dir()]
    )
    collections = [c.strip("/") for c in collections]

    stickers = [s for s in folder.iterdir() if s.is_file()]
    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
    # FIXME : those next two lines seem convoluted, we can probably directly create the Sticker() objets
    stickers = [collection + "/" + str(s.name) for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    sticker_objects = [Sticker(UPLOAD_FOLDER / s) for s in stickers]

    return render_template(
        "index.html",
        current_collection=collection,
        collections=collections,
        stickers=sticker_objects,
        is_root_collection=not bool(collection),
        printer_is_online=os.path.exists(PRINTER),
        fonts=fonts,
    )


@app.route("/rename")
def rename():

    collection = ""
    stickers = [s for s in UPLOAD_FOLDER.iterdir() if s.is_file()]
    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
    stickers = [collection + "/" + str(s.name) for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    sticker_objects = [Sticker(UPLOAD_FOLDER / s) for s in stickers]


    return render_template(
        "rename.html",
        stickers=sticker_objects,
        available_tags=TAGS,
    )


@app.route("/stickers/rename", methods=["GET", "PATCH"])
def rename_sticker():

    if request.method == "PATCH":
        relative = request.form.get("sticker")
        rename = request.form.get("rename")
        tag_add = request.form.get("tag-add")
        tag_remove = request.form.get("tag-remove")

        assert_safe_filename(relative)
        s = Sticker(UPLOAD_FOLDER / relative)

        if tag_add and tag_add not in s.tags:
            s.tags.append(tag_add)
        if tag_remove and tag_remove in s.tags:
            s.tags.remove(tag_remove)
        if rename:
            rename = rename.strip().replace(" ", "_")

        def sticker_already_exists(f: Path, ignore: Path|None =None) -> bool:
           print(f)
           print(f.exists())
           if f.exists():
               return True
           relative_to = f.relative_to(UPLOAD_FOLDER)
           parent = f.parent
           basename = relative_to.name.rsplit(".", 1)[0].split("__")[0]
           matches = list(parent.glob(f"{basename}.*")) + list(parent.glob(f"{basename}__*.*"))
           print(matches)
           if ignore and ignore in matches:
               matches.remove(ignore)
           print(matches)
           return bool(matches)

        previous_path = s.path
        if rename:
            s.name = rename
        new_path = Path(s.metadata_to_path())
        if sticker_already_exists(new_path, ignore=previous_path):
            return error("Il y a déjà un sticker avec ce même nom", code=406)

        s.path.rename(str(new_path))
        s = Sticker(new_path)
    else:
        relative = request.args.get("sticker")
        s = Sticker(UPLOAD_FOLDER / relative)

    return render_template(
        "sticker-rename.html",
        sticker=s,
        available_tags=TAGS,
    )

def error(msg, code=400):
     return render_template("error.html", msg=msg), code

@app.route("/empty")
def empty():
    return ""

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
        assert_safe_filename(collection)
        collection_path = UPLOAD_FOLDER / collection
        assert collection_path.exists()
    else:
        collection_path = UPLOAD_FOLDER

    file = request.files["file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if not file or not file.filename.strip():
        return "Pas de fichier sélectionné !?", 406
    if not allowed_file(file.filename):
        return "Ohno, cette extension n'est pas autorisée!", 406

    filename = secure_filename(file.filename)
    path = collection_path / filename
    if path.exists():
        return "Il existe déjà un fichier avec ce nom", 406
    file.save(path)

    return render_template("sticker.html", sticker=Sticker(path))


@app.route("/stickers/print", methods=["POST"])
def sticker_print():

    if PRINTER != "dummy" and not os.path.exists(PRINTER):
        return "Erreur: l'imprimante est hors ligne / inaccessible !", 400

    try:
        name = request.args.get("sticker")
        quantity = request.form.get("quantity", 1, type=int)
        size = request.form.get("size", "default")

        assert (
            quantity > 0 and quantity < 500
        ), f"La quantité '{quantity}' est incorrecte"
        assert size in [
            "default",
            "large",
            "small",
        ], f"La taille '{size}' est incorrecte"
        assert_safe_filename(name)
        path = UPLOAD_FOLDER / name
        assert path.exists(), f"Le fichier '{name}' n'existe pas ?"
    except Exception as e:
        return f"Erreur: {e}", 400

    try:
        return _sticker_print(str(path), size=size, quantity=quantity)
    except Exception as e:
        import traceback
        return str(traceback.format_list(traceback.extract_stack())), 400
        return "Ohno ! L'impression a échoué ! Il faut regarder les logs !", 400


#@app.route(
#    "/stickers/<collection>/<subcol>/<subsubcol>/print_all", methods=["GET", "POST"]
#)
#def sticker_print_all(collection=None, subcol=None, subsubcol=None):
#    if not collection:
#        collection = ""
#        folder = Path(app.config["UPLOAD_FOLDER"])
#    else:
#        if subcol:
#            collection += "/" + subcol
#        if subsubcol:
#            collection += "/" + subsubcol
#        assert (
#            ".." not in collection and "'" not in collection and ";" not in collection
#        )
#        folder = Path(app.config["UPLOAD_FOLDER"]) / collection
#
#    collections = sorted(
#        [collection + "/" + str(s.name) for s in folder.iterdir() if s.is_dir()]
#    )
#    collections = [c.strip("/") for c in collections]
#
#    stickers = [s for s in folder.iterdir() if s.is_file()]
#    stickers = sorted(stickers, key=lambda f: f.stat().st_mtime, reverse=True)
#    stickers = [collection + "/" + str(s.name) for s in stickers]
#
#    any_failed = False
#    for name in stickers:
#        assert name and ".." not in name and "'" not in name and ";" not in name
#        path = app.config["UPLOAD_FOLDER"] + "/" + name
#        assert Path(path).exists()
#        ret = os.system(f"bash scripts/print.sh '{path}'")
#        if ret != 0:
#            any_failed = True
#
#    return jsonify(success=any_failed is False)


@app.route("/stickers/delete", methods=["DELETE"])
def sticker_delete():
    name = request.args.get("sticker")
    assert_safe_filename(name)
    path = UPLOAD_FOLDER / name
    assert path.exists()
    path.unlink()
    return ""


@app.route("/stickers/search")
def search():

    pattern = request.args.get("q")
    assert pattern.lower().replace(" ", "").replace("_", "").isalnum(), ""

    matches = [
        f
        for f in list(UPLOAD_FOLDER.rglob("*"))
        if f.is_file() and pattern in str(f)
    ]

    stickers = sorted(matches, key=lambda f: f.stat().st_mtime, reverse=True)
    # FIXME : those next two lines seem convoluted, we can probably directly create the Sticker() objets
    stickers = [str(s).replace(str(UPLOAD_FOLDER), "") for s in stickers]
    stickers = [s.strip("/") for s in stickers]

    sticker_objects = [Sticker(UPLOAD_FOLDER / s) for s in stickers]

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
    assert_safe_filename(name)
    path = UPLOAD_FOLDER / name
    assert path.exists()

    with Image.open(path) as im:
        if im.mode != "L":
            im = _decolor_image(im, strength=decolor)

        im = ImageEnhance.Brightness(im).enhance(brightness)
        im = ImageEnhance.Brightness(im).enhance(contrast)
        im = ImageEnhance.Brightness(im).enhance(brightness2)

        if request.method == "POST":
            path_without_ext, ext = str(path).rsplit(".", 1)
            new_name = f"{path_without_ext}_bw{decolor}_b{brightness}c{contrast}b2{brightness2}.{ext}"
            pil_format = ext.upper()
            if pil_format == "JPG":
                pil_format = "JPEG"
            im.save(new_name, format=pil_format)
            return render_template("sticker.html", sticker=Sticker(Path(new_name)))
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
            try:
                return _sticker_print(path, size=print_size, quantity=1)
            except Exception as e:
                print(e)
                return "Ohno ! L'impression a échoué ! Il faut regarder les logs !", 400
        else:
            path = UPLOAD_FOLDER / f"{slug}.png"
            img.save(path, format="PNG")
            return render_template("sticker.html", sticker=Sticker(path))
    else:
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


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


def list_fonts() -> dict:
    if not list(Path("assets/fonts").rglob("*.otf")) + list(Path("assets/fonts").rglob("*.ttf")):
        print("Warning: there's no fonts (.otf or .ttf) at all in assets/fonts/ !")
        return {}

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
    attrs["width"] = size
    attrs["height"] = size
    attrs = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])

    svg = path.read_text(encoding="utf-8")
    svg = re.sub(
        r'width="1em" height="1em"',
        '',
        svg,
        count=1
    )
    svg = re.sub(
        r"<circle ",
        '<circle fill="none"',
        svg,
        count=1,
    )
    svg = re.sub(
        r"<svg(?=[\s>])",
        "<svg " + attrs,
        svg,
        count=1,
    )

    return Markup(svg)


app.jinja_env.globals["icon"] = icon


def _sticker_print(sticker, size="default", quantity=1):

    if not USE_QUEUE:
        return __sticker_print(sticker, size=size, quantity=quantity)
    else:
        q = rq.queues["default"]
        q.enqueue(__sticker_print, sticker=sticker, size=size, quantity=quantity)
        return ""


def __sticker_print(sticker, size="default", quantity=1):

    from brother_ql.conversion import convert
    from brother_ql.backends.helpers import send
    from brother_ql.raster import BrotherQLRaster

    if USE_QUEUE:
        from rq import get_current_job
        j = get_current_job()
        j.meta["quantity_done"] = "processing"
        j.save_meta()

    if size == "default":
        size = DEFAULT_PRINT_SIZE

    with TemporaryDirectory(prefix="stickers_") as d:

        D = Path(d)
        before_dithering = D / "before_dithering.png"
        after_dithering = D / "after_dithering.png"

        with Image.open(sticker) as img:
            img.load()
            # Fix orientation depending if we want to print the image as large or small
            if (size == "large" and img.height > img.width) \
               or (size == "small" and img.width > img.height):
                img = img.transpose(Image.Transpose.ROTATE_90)
            img.save(before_dithering, format="PNG")

        subprocess.run([
            DIDDER_BIN,
            "--height", LABEL_IDEAL_PIXEL_SIZE,
            "--brightness", "0.1",
            "--palette", "black white",
            "--in", str(before_dithering),
            "--out", str(after_dithering),
            "edm",
            "--serpentine", "FloydSteinberg"
        ])

        # Convert image to print instructions
        with Image.open(after_dithering) as img:
            img.load()
            qlr = BrotherQLRaster(PRINTER_MODEL)
            qlr.exception_on_warning = True
            instructions = convert(qlr=qlr, rotate="90", label=LABEL, cut=True, images=[img])

    if USE_QUEUE:
        j.meta["quantity_done"] = 0
        j.save_meta()

    # Actual print using the instructions
    for i in range(quantity):
        if PRINTER == "dummy":
            time.sleep(2)
            ret = None
        else:
            ret = send(instructions=instructions, printer_identifier="file://" + PRINTER, blocking=True)

        print(ret)

        if USE_QUEUE:
            j.meta["quantity_done"] = i+1
            j.save_meta()
        time.sleep(0.1)
        #if not ret['did_print']:
        #    logger.warning("'printing completed' ret not received.")
        #if not ret['ready_for_next_job']:
        #    logger.warning("'waiting to receive' ret not received.")
        #if (not ret['did_print']) or (not ret['ready_for_next_job']):
        #    logger.warning('Printing potentially not successful?')
        #if ret['did_print'] and ret['ready_for_next_job']:
        #    logger.info("Printing was successful. Waiting for the next job.")


if USE_QUEUE == "true":
    from flask_rq import RQ
    from rq.job import Job
    rq = RQ()
    rq.init_app(app)

    @app.route("/queue")
    def queue():
        queue = rq.queues["default"]

        job_ids = set(queue.job_ids)

        registries = [
            queue.started_job_registry,
            queue.finished_job_registry,
            queue.failed_job_registry,
            queue.deferred_job_registry,
            queue.scheduled_job_registry,
            queue.canceled_job_registry,
        ]
        for registry in registries:
            job_ids.update(registry.get_job_ids())

        jobs = Job.fetch_many(list(job_ids), connection=queue.connection)

        def time_human(dt):
            seconds = int(time.time()) - dt.timestamp()
            if seconds is None or seconds > 2592000:
                return "il y a ... super longtemps?!"
            if seconds < 60:
                return f"il y a {int(seconds)} seconde{'s' if int(seconds) != 1 else ''}"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                return f"il y a {minutes} minute{'s' if minutes != 1 else ''}"
            elif seconds < 86400:
                hours = int(seconds // 3600)
                return f"il y a {hours} heure{'s' if hours != 1 else ''}"
            else:
                days = int(seconds // 86400)
                return f"il y a {days} jour{'s' if days != 1 else ''}"

        out = []
        for job in jobs:
            out.append({
                "id": job.id,
                "state": str(job.get_status()).split(".")[-1].lower(),
                "enqueued_at_timestamp": job.enqueued_at.timestamp(),
                "enqueued_at": time_human(job.enqueued_at),
                "sticker": job.kwargs["sticker"],
                "quantity": job.kwargs["quantity"],
                "size": job.kwargs["size"],
            })
            if job.get_status() in ["started", "finished", "failed"]:
                out[-1]["quantity_done"] = job.get_meta().get("quantity_done", None)

        out = sorted(out, key=lambda j: j['enqueued_at_timestamp'], reverse=True)

        return render_template("queue.html", jobs=out)
