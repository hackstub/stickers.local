import { StickerImage } from "./sticker-image.js";

customElements.define("sticker-image", StickerImage);

document.getElementById("modal-advanced-print-button").addEventListener("click", function (event) {
    event.preventDefault();
    document.getElementById("modal-advanced-print-error").textContent = "";
    var sticker = document.getElementById("modal-advanced-print").getAttribute("data-sticker");
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
        document.getElementById("modal-advanced-print").classList.add("hidden");
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

function updateProcessImage() {
    var sticker = document.getElementById("modal-processing").getAttribute("data-sticker");
    var brightness = document.querySelector("#modal-processing input[name='brightness']").value;
    var contrast = document.querySelector("#modal-processing input[name='contrast']").value;
    var brightness2 = document.querySelector("#modal-processing input[name='brightness2']").value;

    fetch(
      window.STICKER_PROCESS_URL +
        `?sticker=${sticker}&brightness=${brightness}&contrast=${contrast}&brightness2=${brightness2}`,
      { method: "GET" },
    )
      .then((response) => response.text())
      .then((data) => {
          document.getElementById("processed_image").src = data
      })
}

var processInputs = document.querySelectorAll("#modal-processing input[name='brightness'], #modal-processing input[name='brightness2'], #modal-processing input[name='contrast']")
for (var i = 0; i < processInputs.length; i++) { processInputs[i].addEventListener('input', updateProcessImage); }

document.getElementById("modal-processing-button").addEventListener("click", function (event) {
    event.preventDefault();
    var sticker = document.getElementById("modal-processing").getAttribute("data-sticker");
    var brightness = document.querySelector("#modal-processing input[name='brightness']").value;
    var contrast = document.querySelector("#modal-processing input[name='contrast']").value;
    var brightness2 = document.querySelector("#modal-processing input[name='brightness2']").value;
    fetch(
      window.STICKER_PROCESS_URL +
        `?sticker=${sticker}&brightness=${brightness}&contrast=${contrast}&brightness2=${brightness2}`,
      { method: "POST" },
    )
    .then((response) => {
        if (response.ok) { location.reload(); }
    });
})


document.onkeydown = function (evt) {
  evt = evt || window.event;
  var isEscape = false;
  if ("key" in evt) {
    isEscape = evt.key === "Escape" || evt.key === "Esc";
  } else {
    isEscape = evt.keyCode === 27;
  }
  if (isEscape) {
    document.getElementById("modal-advanced-print").classList.add("hidden");
    document.getElementById("modal-processing").classList.add("hidden");
  }
};
