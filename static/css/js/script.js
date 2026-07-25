console.log("PricingAI Loaded Successfully");

document.addEventListener("DOMContentLoaded", function () {

    const cards = document.querySelectorAll(".card");

    cards.forEach(function (card) {

        card.addEventListener("mouseover", function () {

            card.style.transform = "scale(1.05)";

        });

        card.addEventListener("mouseout", function () {

            card.style.transform = "scale(1)";

        });

    });

});