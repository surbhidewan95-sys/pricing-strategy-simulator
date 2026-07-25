document.addEventListener("DOMContentLoaded", function () {
    const button = document.getElementById("themeButton");

    if (button) {
        button.addEventListener("click", function () {
            // Check karein ki abhi background dark hai ya light
            const currentBg = getComputedStyle(document.body).backgroundColor;

            // Agar background dark tone hai (#162436 ya default dark), toh light theme kar do
            if (document.body.classList.contains("light-mode")) {
                document.body.classList.remove("light-mode");
                document.body.style.backgroundColor = "#0f172a"; // Dark Mode
                document.body.style.color = "#ffffff";
            } else {
                document.body.classList.add("light-mode");
                document.body.style.backgroundColor = "#f8fafc"; // Light Mode
                document.body.style.color = "#0f172a";
            }
        });
    }
});