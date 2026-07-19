import { decode } from "/assets/blurhash.min.js";

export class StickerImage extends HTMLElement {

  connectedCallback() {

    // Get attributes
    const hash = this.getAttribute("hash");
    const src = this.getAttribute("src");
    const width = parseInt(this.getAttribute("width"));
    const height = parseInt(this.getAttribute("height"));
    const sticker = this.getAttribute("sticker");

    // Get placeholder element
    const placeholder = this.querySelector("#sticker-image");

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
    this
      .querySelector(".print")
      .addEventListener("click", this.printHandler(sticker));

    // Delete button
    this
      .querySelector(".delete")
      .addEventListener("click", this.deleteHandler(sticker));

    // Advanced print button
    this
      .querySelector(".advanced-print")
      .addEventListener("click", this.advancedPrintHandler(sticker));

    // Process image
    this
      .querySelector(".process-image")
      .addEventListener("click", this.processImageHandler(sticker));
  }

  advancedPrintHandler = (sticker) => (e) => {
    document.getElementById("modal-advanced-print").classList.toggle("hidden");
    document.getElementById("modal-advanced-print").classList.toggle("grid");
    document.getElementById("modal-advanced-print").dataset.sticker = sticker;
    document.getElementById("modal-advanced-print-error").textContent = "";
    document.getElementById("modal-advanced-print-sticker").textContent = sticker;
  };

  processImageHandler = (sticker) => (e) => {
    document.getElementById("modal-processing").classList.toggle("hidden");
    document.getElementById("modal-processing").classList.toggle("grid");
    document.getElementById("modal-processing").dataset.sticker = sticker;
    document.getElementById("modal-processing-sticker").textContent = sticker;
    // Trigger dummy even to trigger the process preview update
    document.querySelector("#modal-processing input[name='brightness']").dispatchEvent(new Event('input'));
  };

  printHandler = (sticker) => (e) => {
    fetch(window.STICKER_PRINT_URL + `?sticker=${sticker}`, {
      method: "POST",
    })
    .then((r) => r.json())
    .then((data) => {
      if (!data.success) {
        document.getElementById("toast").classList.remove("hidden");
        document.getElementById("toast").classList.add("grid");
        document.getElementById("toast-error").textContent = "Ohno, une impression a échoué ! Il faut regarder les logs !";
        setTimeout(
          () => { document.getElementById("toast").classList.add("hidden"); document.getElementById("toast").classList.add("grid") },
          5000,
        );
      }
    });
  };

  deleteHandler = (sticker) => () => {
    fetch(window.STICKER_DELETE_URL + `?sticker=${sticker}`, {
      method: "DELETE",
    });
    this.remove();
  };
}
