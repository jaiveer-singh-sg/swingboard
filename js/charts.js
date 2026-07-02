function drawTechnicalChart(stock) {

    const canvas = document.getElementById("chart_" + stock["Ticker"]);

    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    // Destroy existing chart before redrawing
    if (chartInstances[stock["Ticker"]]) {
        chartInstances[stock["Ticker"]].destroy();
    }

    chartInstances[stock["Ticker"]] = new Chart(ctx, {

        type: "bar",

        data: {

            labels: [
                "Support",
                "20 SMA",
                "50 SMA",
                "Price",
                "200 SMA",
                "Resistance"
            ],

            datasets: [{

                label: stock["Ticker"],

                data: [
                    stock.support,
                    stock.sma20,
                    stock.sma50,
                    stock.price,
                    stock.sma200,
                    stock.resistance
                ]

            }]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            indexAxis: "y",

            plugins: {

                legend: {
                    display: false
                }

            },

            scales: {

                x: {

                    beginAtZero: false

                }

            }

        }

    });

}

function renderAllCharts(stocks){

    stocks.forEach(stock => {
        drawTechnicalChart(stock);
    });

}
