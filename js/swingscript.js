/**********************************************************************
    PAGE LOAD
**********************************************************************/

window.addEventListener("DOMContentLoaded", async () => {

    wireButtons();
	initFilters();
    await loadDefaultCSV();

});


/**********************************************************************
    BUTTON EVENTS
**********************************************************************/

function wireButtons(){

    document
        .getElementById("browseBtn")
        .onclick = () =>
            document
                .getElementById("csvFileInput")
                .click();

    document
        .getElementById("csvFileInput")
        .addEventListener("change", handleFileUpload);

    document
        .getElementById("refreshBtn")
        .addEventListener("click", refreshUploadedData);

    document
        .getElementById("reloadBtn")
        .addEventListener("click", loadDefaultCSV);


}
