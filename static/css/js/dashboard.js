window.onload = function () {
    const canvas = document.getElementById("myChart");

    if (canvas) {
        const ctx = canvas.getContext("2d");

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["January", "February", "March", "April"],
                datasets: [{
                    label: "Revenue (₹)",
                    data: [12000, 19000, 15000, 22000],
                    backgroundColor: "rgba(0, 210, 255, 0.6)",
                    borderColor: "rgba(0, 210, 255, 1)",
                    borderWidth: 1.5,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff', // Light text for dark background
                            font: {
                                size: 14
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#ffffff' // White month labels
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)' // Subtle grid line
                        }
                    },
                    y: {
                        ticks: {
                            color: '#ffffff' // White numbers scale
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
};