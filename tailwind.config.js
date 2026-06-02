/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./js/**/*.html"],
  theme: {
    extend: {},
  },
  plugins: [require("@tailwindcss/forms")],
};
