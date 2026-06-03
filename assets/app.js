import { StickerImage } from "./sticker-image.js";

customElements.define("sticker-image", StickerImage);

document
  .getElementById("modal-print")
  .addEventListener("click", function (event) {
    event.preventDefault();
    document.getElementById("modal-error").textContent = "";
    var sticker = document.getElementById("modal").getAttribute("data-sticker");
    var size = document.getElementById("modal-print-size").value;
    var quantity = document.getElementById("modal-print-quantity").value;
    fetch(
      window.STICKER_PRINT_URL +
        `?quantity=${quantity}&size=${size}&sticker=${sticker}`,
      { method: "POST" },
    )
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          document.getElementById("modal").classList.add("hidden");
        } else {
          document.getElementById("modal-error").textContent =
            "Ohno, l'impression a échoué! Il faut regarder les logs!";
        }
      });
  });

document.getElementById("search").addEventListener("keyup", function (event) {
  event.preventDefault();
  if (event.keyCode === 13) {
    location.replace(
      window.STICKER_SEARCH_URL +
        "?q=" +
        document.getElementById("search").value,
    );
  }
});

document.onkeydown = function (evt) {
  evt = evt || window.event;
  var isEscape = false;
  if ("key" in evt) {
    isEscape = evt.key === "Escape" || evt.key === "Esc";
  } else {
    isEscape = evt.keyCode === 27;
  }
  if (isEscape) {
    document.getElementById("modal").classList.add("hidden");
  }
};
