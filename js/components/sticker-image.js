import { decode } from "blurhash";
import TEMPLATE from "./sticker-image.html";

export class StickerImage extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    this.shadowRoot.innerHTML = TEMPLATE;

    // Get attributes
    const hash = this.getAttribute("hash");
    const src = this.getAttribute("src");
    const width = parseInt(this.getAttribute("width"));
    const height = parseInt(this.getAttribute("height"));
    const sticker = this.getAttribute("sticker");

    // Get placeholder element
    const placeholder = this.shadowRoot.querySelector("#sticker-image");

    // Decode blurhash at a small size, scale up with CSS
    const SCALE = 32;
    const aspect = width / height;
    const bw = aspect >= 1 ? SCALE : Math.round(SCALE * aspect);
    const bh = aspect < 1 ? SCALE : Math.round(SCALE / aspect);
    const pixels = decode(hash, bw, bh);
    const canvas = document.createElement("canvas");
    canvas.width = bw;
    canvas.height = bh;
    canvas.className = placeholder.className;
    canvas.style.imageRendering = "auto";
    const ctx = canvas.getContext("2d");
    const imageData = ctx.createImageData(bw, bh);
    imageData.data.set(pixels);
    ctx.putImageData(imageData, 0, 0);

    // Replace placeholder with blurhash canvas
    placeholder.replaceWith(canvas);

    // Trigger actual image loading
    const image = new Image();
    image.className = canvas.className;
    image.onload = () => canvas.replaceWith(image);
    image.src = src;

    // Print button
    this.shadowRoot
      .querySelector(".print")
      .addEventListener("click", this.printHandler(sticker));

    // Delete button
    this.shadowRoot
      .querySelector(".delete")
      .addEventListener("click", this.deleteHandler(sticker));
  }

  printHandler = (sticker) => (e) => {
    if (e.ctrlKey) {
      document.getElementById("modal").classList.toggle("hidden");
      document.getElementById("modal-error").textContent = "";
      document.getElementById("modal").dataset.sticker = sticker;
      document.getElementById("modal-sticker-name").textContent = sticker;
    } else {
      fetch(window.STICKER_PRINT_URL + `?sticker=${sticker}`, {
        method: "POST",
      })
        .then((r) => r.json())
        .then((data) => {
          if (!data.success) {
            document.getElementById("toast").classList.remove("hidden");
            document.getElementById("toast-error").textContent =
              "Ohno, une impression a échoué! Il faut regarder les logs!";
            setTimeout(
              () => document.getElementById("toast").classList.add("hidden"),
              2000,
            );
          }
        });
    }
  };

  deleteHandler = (sticker) => () => {
    fetch(window.STICKER_DELETE_URL + `?sticker=${sticker}`, {
      method: "DELETE",
    });
    this.remove();
  };
}
