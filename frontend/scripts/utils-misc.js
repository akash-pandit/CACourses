function shortenUniName(name) {
    if (!name) return '';
    return name
        .replace("University of California,", "UC")
        .replace("California State University,", "Cal State")
        .replace("California Polytechnic University,", "Cal Poly")
        .replace("State University", "State")
        .replace("San Luis Obispo", "SLO");
}

function getCCName(cc_id) {
    return window.ccMap?.[cc_id] || `ID: ${cc_id}`
}

window.ccMap = {}; 
fetchCCMap().then(data => window.ccMap = data);
