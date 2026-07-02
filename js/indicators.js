/**********************************************************************
    CALCULATE INDICATORS
**********************************************************************/

function calculateIndicators(stock){

    const price=num(stock["Price ($)"]);

    const sma20=num(stock["20 SMA ($)"]);

    const sma50=num(stock["50 SMA ($)"]);

    const sma200=num(stock["200 SMA ($)"]);

    const support=num(stock["Support ($)"]);

    const resistance=num(stock["Resistance ($)"]);

    const target=num(stock["Mean Target ($)"]);

    const rsi=num(stock["RSI (14)"]);

    const vwap=num(stock["VWAP ($)"]);

    stock.price=price;

    stock.sma20=sma20;

    stock.sma50=sma50;

    stock.sma200=sma200;

    stock.support=support;

    stock.resistance=resistance;

    stock.target=target;

    stock.rsi=rsi;

    stock.vwap=vwap;

    stock.above20=price>sma20;

    stock.above50=price>sma50;

    stock.above200=price>sma200;

    stock.aboveVWAP=price>vwap;

    stock.supportDistance=
        ((price-support)/support*100);

    stock.resistanceDistance=
        ((resistance-price)/price*100);

    stock.targetUpside=
        ((target-price)/price*100);

    stock.rsiStatus=getRSIStatus(rsi);

    stock.recommendation=getRecommendation(stock);

    stock.swingScore=calculateSwingScore(stock);

}

function getRSIStatus(rsi){

    if(rsi<35)
        return "Oversold";

    if(rsi<45)
        return "Weak";

    if(rsi<=65)
        return "Healthy";

    if(rsi<=75)
        return "Strong";

    return "Overbought";

}

function getRecommendation(s){

    if(

        s.above20 &&

        s.above50 &&

        s.above200 &&

        s.rsi>=50 &&

        s.rsi<=65 &&

        s["Vol Breakout"]?.includes("YES")

    )

        return "STRONG BUY";

    if(

        s.above50 &&

        s.rsi>45

    )

        return "BUY";

    if(

        s.supportDistance<3 ||

        s.resistanceDistance<2

    )

        return "WATCH";

    if(!s.above50)

        return "WEAK";

    return "AVOID";

}

function calculateSwingScore(s){

    let score=0;

    if(s.above20) score+=15;

    if(s.above50) score+=15;

    if(s.above200) score+=20;

    if(s.aboveVWAP) score+=10;

    if(s.rsi>=45 && s.rsi<=65)
        score+=15;

    if(s["Vol Breakout"]?.includes("YES"))
        score+=15;

    if(s.targetUpside>20)
        score+=10;

    return Math.min(100,score);

}

