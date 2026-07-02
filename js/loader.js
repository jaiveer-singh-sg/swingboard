
/**********************************************************************
    LOAD DEFAULT CSV
**********************************************************************/

async function loadDefaultCSV(){

    try{

        const response = await fetch("data/tickersdata.csv");

        uploadedCSV = await response.text();

        parseCSV(uploadedCSV);

    }

    catch(err){

        alert("Unable to load tickersdata.csv");

        console.error(err);

    }

}


/**********************************************************************
    USER FILE
**********************************************************************/

async function handleFileUpload(e){

    const file = e.target.files[0];

    if(!file) return;

    uploadedCSV = await file.text();

}


/**********************************************************************
    REFRESH
**********************************************************************/

function refreshUploadedData(){

    if(uploadedCSV===""){

        alert("Please choose a CSV first.");

        return;

    }

    parseCSV(uploadedCSV);

}

function updateStatus(msg){

    document.getElementById("statusBar").textContent=msg;

}