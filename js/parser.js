
/**********************************************************************
    CSV PARSER
**********************************************************************/

function parseCSV(text){

    dashboardData=[];

    const rows=text
        .split(/\r?\n/)
        .filter(x=>x.trim()!="");

    if(rows.length<2){

        alert("CSV empty.");

        return;

    }

    const separator =
        rows[0].includes("\t")
        ? "\t"
        : ",";

    const headers=
        rows[0]
        .split(separator)
        .map(x=>clean(x));

    for(let i=1;i<rows.length;i++){

        const cols=
            rows[i]
            .split(separator)
            .map(x=>clean(x));

        if(cols.length<headers.length)
            continue;

        let stock={};

        headers.forEach((h,index)=>{

            stock[h]=cols[index];

        });

        calculateIndicators(stock);

        dashboardData.push(stock);

    }

    renderDashboard();

}


/**********************************************************************
    CLEAN STRING
**********************************************************************/

function clean(txt){

    return txt
        .replace(/^"/,"")
        .replace(/"$/,"")
        .trim();

}


/**********************************************************************
    NUMBER
**********************************************************************/

function num(v){

    return parseFloat(
        String(v)
        .replace(/,/g,"")
        .replace("$","")
        .replace("%","")
    )||0;

}
