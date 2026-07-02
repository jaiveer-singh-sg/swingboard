
function buildHeatmap(stocks){

const div=document.getElementById("heatmapContainer");

let html=`

<table class="heatmapTable">

<tr>

<th>Ticker</th>

<th>Trend</th>

<th>RSI</th>

<th>Volume</th>

<th>Support</th>

<th>Reward</th>

</tr>

`;

stocks.forEach(s=>{

html+=`

<tr>

<td class="heatTicker"

onclick="scrollToTicker('${s["Ticker"]}')">

${s["Ticker"]}

</td>

<td>

${trendIcons(s)}

</td>

<td>

${rsiColor(s)}

</td>

<td>

${s["Vol Breakout"]?.includes("YES")

?'<span class="heatGreen">🚀</span>'

:'-'}

</td>

<td>

${supportStatus(s)}

</td>

<td>

${rewardStatus(s)}

</td>

</tr>

`;

});

html+="</table>";

div.innerHTML=html;

}