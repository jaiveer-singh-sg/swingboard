
function initFilters() {

    document.querySelectorAll(".filterBtn").forEach(btn => {

        btn.addEventListener("click", function () {

            document.querySelectorAll(".filterBtn")
                .forEach(b => b.classList.remove("activeFilter"));

            this.classList.add("activeFilter");

            currentFilter = this.textContent.trim().toLowerCase();

            renderDashboard();

        });

    });
    document
        .getElementById("searchBox")
        .addEventListener("input", e=>{

            searchText=e.target.value.toUpperCase();

            renderDashboard();

        });

    document
        .getElementById("sortSelect")
        .addEventListener("change",e=>{

            currentSort=e.target.value;

            renderDashboard();

        });
}
function applyFilter(stocks) {

    switch (currentFilter) {

        case "bullish":
            return stocks.filter(s =>
                s.recommendation === "BUY" ||
                s.recommendation === "STRONG BUY"
            );

        case "bearish":
            return stocks.filter(s =>
                s.recommendation === "AVOID"
            );

        case "breakouts":
            return stocks.filter(s =>
                s["Vol Breakout"] &&
                s["Vol Breakout"].toUpperCase().includes("YES")
            );

        case "near support":
            return stocks.filter(s =>
                s.supportDistance <= 3
            );

        case "near resistance":
            return stocks.filter(s =>
                s.resistanceDistance <= 3
            );

        case "above 200 sma":
            return stocks.filter(s =>
                s.above200
            );

        default:
            return stocks;
    }

}

function applySearch(stocks) {

    if (searchText === "")
        return stocks;

    return stocks.filter(s =>
        s["Ticker"]
            .toUpperCase()
            .includes(searchText.toUpperCase())
    );

}

function applySort(stocks) {

    switch (currentSort) {

        case "daily":

            stocks.sort((a, b) =>
                Number(b["Daily Chg (%)"]) -
                Number(a["Daily Chg (%)"])
            );

            break;

        case "weekly":

            stocks.sort((a, b) =>
                Number(b["Weekly Chg (%)"]) -
                Number(a["Weekly Chg (%)"])
            );

            break;

        case "price":

            stocks.sort((a, b) =>
                b.price - a.price
            );

            break;

        case "reward":

            stocks.sort((a, b) =>
                b.targetUpside - a.targetUpside
            );

            break;

        case "rsi":

            stocks.sort((a, b) =>
                b.rsi - a.rsi
            );

            break;

        default:

            stocks.sort((a, b) =>
                b.swingScore - a.swingScore
            );

    }

    return stocks;

}