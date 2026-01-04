const GET_ARTICULATIONS_LAMBDA_URL = 'https://5eqjf6ysqgsoyr2ln34dfigeim0naiez.lambda-url.us-west-1.on.aws';
const GET_COURSES_LAMBDA_URL = 'https://kedlmmemb2qvdqlzu5srtnqoi40icpqk.lambda-url.us-west-1.on.aws';

/**
 * Retrieves articulation agreements and maps IDs to course details.
 * @param {string} courseID - ID from the search input.
 * @returns {Promise<Array<Array<{string, string}>>>} {cc: [[{code, name}, ...], ...], ...}
 */
async function _fetchArticulations(courseID) {
    const response = await fetch(`${GET_ARTICULATIONS_LAMBDA_URL}/?course_id=${encodeURIComponent(courseID)}`);

    if (!response.ok) throw new Error("Failed to fetch articulation data");

    const [articulations, courses] = await response.json();

    const result = Object.fromEntries(
        Object.entries(articulations).map(([cc, jsonstr]) => {
            try {
                const agreement = JSON.parse(jsonstr);
                const matrix = agreement.items.map(andblock => 
                    andblock.items.map(
                        id => ({
                            code: courses[id]?.course_code ?? "Unknown",
                            name: courses[id]?.course_name ?? "Unknown"
                        })
                    )
                )
                return [cc, matrix];
            } catch (e) {
                console.error("Invalid JSON for CC:", cc);
                return [cc, []]; // Fallback for failed parses
            }
        })
    )
    console.log(result);
    return result;
}

async function fetchCCMap() {
    resp = await fetch("institutions_cc.json")
    if (!resp.ok) throw new Error("Couldn't load institutions_cc.json")
    return await resp.json()
}

window.ccMap = {}; 
fetchCCMap().then(data => window.ccMap = data);
