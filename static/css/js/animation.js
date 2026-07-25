document.addEventListener("DOMContentLoaded", function () {

    const title = document.querySelector(".hero h1");

    const text = "AI Pricing Strategy Simulator";

    let index = 0;

    function typingEffect() {

        if (index < text.length) {

            title.innerHTML += text.charAt(index);

            index++;

            setTimeout(typingEffect, 100);

        }
    }

    title.innerHTML = "";

    typingEffect();

});