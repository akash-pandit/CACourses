/**
 * Retrieves articulation agreements and maps IDs to course details.
 * @param {string} courseID - ID from the search input.
 * @returns {Promise<Array<Array<{string, string}>>>} {cc: [[{code, name}, ...], ...], ...}
 */
async function _fetchArticulations(courseID) {
    const API = 'https://5eqjf6ysqgsoyr2ln34dfigeim0naiez.lambda-url.us-west-1.on.aws';
    
    const response = await fetch(`${API}/?course_id=${encodeURIComponent(courseID)}`);

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


async function getCoursesArray(univID, cache) {
    // console.log(`getCoursesArray(${courseID}, courseCache)`)
    if (univID in cache) { return cache[univID]; }

    try {
        const API_COURSES = 'https://lzlnwhushmmp5jnpzqed6x4qa40dfsjr.lambda-url.us-west-1.on.aws'; 
        // console.log(`sending request to ${API_COURSES}/?uni=${encodeURIComponent(univID)}`);
        const result = await fetch(`${API_COURSES}/?uni=${encodeURIComponent(univID)}`);
        const courses = await result.json();
        const sortedCourses = courses.sort((a, b) => a.course_code.localeCompare(b.course_code));
            
        cache[univID] = sortedCourses;
        return sortedCourses;

    } catch (error) { console.error("Error fetching courses:", error); return []; }
}


async function getArticulationsArray(courseID, cache) {
    // console.log(`getArticulationsArray(${courseID}, artiCache)`)
    if (courseID in cache) { return cache[courseID]; }

    try {
        const API_ARTS    = 'https://z26wqyts4e52be3njzagavub3e0xxusm.lambda-url.us-west-1.on.aws';
        // console.log(`sending request to ${API_ARTS}/?course_id=${encodeURIComponent(courseID)}`);
        const result = await fetch(`${API_ARTS}/?course_id=${encodeURIComponent(courseID)}`);
        const [agreements, courses] = await result.json();
        
        cache[courseID] = [agreements, courses];
        return [agreements, courses];

    } catch (error) { console.error("Error fetching articulations:", error); return []; }
}