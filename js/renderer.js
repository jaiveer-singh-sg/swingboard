/********************************************************************
    MAIN RENDER
********************************************************************/

function renderDashboard() {

    let stocks = [...dashboardData];

    stocks = applySearch(stocks);

    stocks = applyFilter(stocks);

    stocks = applySort(stocks);

    buildSummary(stocks);

    buildHeatmap(stocks);

    buildTickerCards(stocks);

}

/********************************************************************
SUMMARY
********************************************************************/

function buildSummary(stocks){

    const summary=document.getElementById("summaryCards");

    const bullish=stocks.filter(x=>x.recommendation=="BUY" || x.recommendation=="STRONG BUY").length;

    const bearish=stocks.filter(x=>x.recommendation=="AVOID").length;

    const watch=stocks.filter(x=>x.recommendation=="WATCH").length;

    const avgRSI=

        (

            stocks.reduce((t,s)=>t+s.rsi,0)

            /

            stocks.length

        ).toFixed(1);

    const breakout=

        stocks.filter(s=>

            s["Vol Breakout"]?.includes("YES")

        ).length;

    const best=stocks[0];

    summary.innerHTML=`

<div class="summaryCard">

<div class="summaryTitle">Stocks</div>

<div class="summaryValue">${stocks.length}</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Bullish</div>

<div class="summaryValue good">${bullish}</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Watch</div>

<div class="summaryValue warning">${watch}</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Bearish</div>

<div class="summaryValue bad">${bearish}</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Avg RSI</div>

<div class="summaryValue">${avgRSI}</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Breakouts</div>

<div class="summaryValue">${breakout}</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Top Pick</div>

<div class="summaryValue">

${best["Ticker"]}

</div>

</div>

<div class="summaryCard">

<div class="summaryTitle">Top Score</div>

<div class="summaryValue">

${best.swingScore}

</div>

</div>

`;

}

/********************************************************************
STOCK CARDS
********************************************************************/

function buildTickerCards(stocks){

    const container = document.getElementById("tickerContainer");
    container.innerHTML = "";

    stocks.forEach((stock, index) => {
        container.insertAdjacentHTML(
            "beforeend",
            createCard(stock, index)
        );
    });

    renderAllCharts(stocks);
}

function ribbonClass(r){

    if(r=="STRONG BUY") return "buy";

    if(r=="BUY") return "buy";

    if(r=="WATCH") return "watch";

    return "avoid";

}

function createCard(s,index){

return `

<div class="stockCard">

<div class="cardHeader">

<div>

<div class="ribbon ${ribbonClass(s.recommendation)}">

${s.recommendation}

</div>

<h2 style="margin-top:10px">

#${index+1}

&nbsp;

${s["Ticker"]}

</h2>

<div style="font-size:24px;font-weight:bold">

$${s.price.toFixed(2)}

</div>

<div>

<span class="${num(s["Daily Chg (%)"])>=0?'good':'bad'}">

${s["Daily Chg (%)"]}%

</span>

|

Week

${s["Weekly Chg (%)"]}%

</div>

</div>

<div style="width:250px">

<div>

Swing Score

${s.swingScore}/100

</div>

<div class="scoreBar">

<div

class="scoreFill"

style="width:${s.swingScore}%">

</div>

</div>

</div>

</div>

${createWidgets(s)}

${createGauge(s)}

${createDetails(s)}

</div>

`;

}

function badge(v){

return v

?

'<span class="good">🟢 YES</span>'

:

'<span class="bad">🔴 NO</span>';

}

function createWidgets(s){

return `

<div class="widgetGrid">

<div class="widget">

<div class="widgetTitle">

20 SMA

</div>

<div class="widgetValue">

${badge(s.above20)}

</div>

</div>

<div class="widget">

<div class="widgetTitle">

50 SMA

</div>

<div class="widgetValue">

${badge(s.above50)}

</div>

</div>

<div class="widget">

<div class="widgetTitle">

200 SMA

</div>

<div class="widgetValue">

${badge(s.above200)}

</div>

</div>

<div class="widget">

<div class="widgetTitle">

VWAP

</div>

<div class="widgetValue">

${badge(s.aboveVWAP)}

</div>

</div>

<div class="widget">

<div class="widgetTitle">

RSI

</div>

<div class="widgetValue">

${s.rsiStatus}

</div>

</div>

<div class="widget">

<div class="widgetTitle">

Reward

</div>

<div class="widgetValue good">

${s.targetUpside.toFixed(1)}%

</div>

</div>

</div>

`;

}

function createGauge(s){

const pct=

Math.max(

0,

Math.min(

100,

((s.price-s.support)/(s.resistance-s.support))*100

)

);

return `

<div style="padding:20px">

<div>

Support

&nbsp;

$${s.support}

</div>

<div class="gauge">

<div

class="gaugeFill"

style="width:100%">

</div>

<div

class="gaugeMarker"

style="left:calc(${pct}% - 9px)">

</div>

</div>

<div style="display:flex;justify-content:space-between">

<span>

Support

</span>

<span>

Price

</span>

<span>

Resistance

</span>

</div>

<div style="display:flex;justify-content:space-between">

<span>

$${s.support}

</span>

<span>

$${s.price}

</span>

<span>

$${s.resistance}

</span>

</div>

</div>

`;

}

function createDetails(s){

return `

<div class="details">

<div style="height:220px;">
    <canvas id="chart_${s["Ticker"]}"></canvas>
</div>

<div>

<table class="metricTable">

<tr>

<td>Target</td>

<td>$${s.target}</td>

</tr>

<tr>

<td>Support</td>

<td>$${s.support}</td>

</tr>

<tr>

<td>Resistance</td>

<td>$${s.resistance}</td>

</tr>

<tr>

<td>ATR</td>

<td>${s["ATR ($)"]}</td>

</tr>

<tr>

<td>Beta</td>

<td>${s["Beta"]}</td>

</tr>

<tr>

<td>Volume</td>

<td>${s["Last Wk Vol"]}</td>

</tr>

<tr>

<td>Average</td>

<td>${s["Avg Wk Vol"]}</td>

</tr>

</table>

</div>

</div>

`;

}

function trendIcons(s){

let txt="";

txt+=s.above20?"🟢":"⚪";

txt+=s.above50?"🟢":"⚪";

txt+=s.above200?"🟢":"⚪";

return txt;

}

function supportStatus(s){

if(s.supportDistance<3)

return '<span class="heatYellow">Near</span>';

if(s.supportDistance<0)

return '<span class="heatRed">Broken</span>';

return '<span class="heatGreen">Safe</span>';

}

function rewardStatus(s){

if(s.targetUpside>25)

return '<span class="heatGreen">High</span>';

if(s.targetUpside>10)

return '<span class="heatYellow">Med</span>';

return '<span class="heatRed">Low</span>';

}

function rsiColor(s){

if(s.rsi>=45 && s.rsi<=65)

return '<span class="heatGreen">'+s.rsi+'</span>';

if(s.rsi<40 || s.rsi>75)

return '<span class="heatRed">'+s.rsi+'</span>';

return '<span class="heatYellow">'+s.rsi+'</span>';

}

function scrollToTicker(ticker){

const card=document.getElementById("card_"+ticker);

if(!card) return;

card.scrollIntoView({

behavior:"smooth",

block:"center"

});

}
