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
