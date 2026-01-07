// app.js
const courseCache = {};
const artiCache = {};

document.addEventListener('alpine:init', () => {
    Alpine.data('alpineMain', () => ({
        // --- State ---
        activeIndex: -1,
        blurTimeout: null,
        loadingUnis: true,
        unis: [],
        univSearching: '',
        univ: null,
        univID: null,
        showUniOpts: false,

        loadingCourses: false,
        courses: [],
        courseSearching: '',
        course: null,
        courseID: null,
        showCourseOpts: false,

        loadingArticulations: false,
        articulations: [],
        showArticulationBlock: false,

        // --- Initialization ---
        init() {
            fetch('institutions_state.json')
                .then(response => response.json())
                .then(data => {
                    this.unis = Object.entries(data)
                        .map(([k, v]) => [v, k])
                        .sort(([n1], [n2]) => n1.localeCompare(n2));
                    this.loadingUnis = false;
                })
                .catch(err => console.error('Error fetching institutions:', err));
        },

        // --- Getters (Computed Logic) --
        get searchUnis() {
            const term = this.univSearching.toLowerCase();
            return this.unis.filter(([name]) => {
                const nameLower = name.toLowerCase();
                const nameShort = nameLower
                    .replaceAll('university of california,', 'uc')
                    .replaceAll('california state university,', 'csu')
                    .replaceAll('california polytechnic university', 'cal poly calpoly')
                    .replaceAll('san luis obispo', 'slo');
                const nameAcro = name.replace('Polytechnic University', 'Poly')
                    .replace(/[^A-Z]/g, '').toLowerCase();

                return nameLower.includes(term) || nameShort.includes(term) || nameAcro.includes(term);
            });
        },

        get searchCourses() {
            const term = this.courseSearching.toLowerCase();
            return this.courses.filter((course) => {
                return course.course_name.toLowerCase().includes(term) || 
                       course.course_code.toLowerCase().includes(term);
            });
        },

        // --- Methods ---
        async selectUni(name, id) {
            this.showUniOpts = false;
            this.showArticulationBlock = false;
            if (id != this.univID) {
                this.univSearching = '';
                this.univ = name;
                this.univID = id;
                this.courseSearching = '';
                this.course = null;
                this.courseID = null;
                await this.fetchCourses();
            }
            if (this.blurTimeout) clearTimeout(this.blurTimeout);
        },

        // TODO: refactor to use a _fetchCourses
        async fetchCourses() {
            if (this.univID in courseCache) {
                this.courses = courseCache[this.univID];
                return;
            }
            this.loadingCourses = true;
            try {
                const API = 'https://lzlnwhushmmp5jnpzqed6x4qa40dfsjr.lambda-url.us-west-1.on.aws';
                const result = await fetch(`${API}/?uni=${encodeURIComponent(this.univID)}`);
                const data = await result.json();
                this.courses = data.sort((a, b) => a.course_code.localeCompare(b.course_code));
                courseCache[this.univID] = this.courses;
            } catch (error) {
                console.error("Error fetching courses:", error);
            } finally {
                this.loadingCourses = false;
            }
        },

        async selectCourse(code, id) {
            this.showCourseOpts = false;
            if (id != this.courseID) {
                this.courseSearching = '';
                this.course = code;
                this.courseID = id;
                await this.fetchArticulations();
            }
            this.showArticulationBlock = true;
        },

        async fetchArticulations() {
            if (this.courseID in artiCache) {
                this.articulations = artiCache[this.courseID];
                return;
            }
            this.loadingArticulations = true;
            try {
                this.articulations = await _fetchArticulations(this.courseID);
                artiCache[this.courseID] = this.articulations;
            } catch (error) {
                console.error("Error fetching articulations:", error);
            } finally {
                this.loadingArticulations = false;
            }
        },

        handleKeydown(event, type) {
            const results = type === 'uni' ? this.searchUnis : this.searchCourses;
            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    this.activeIndex = (this.activeIndex + 1) % results.length;
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    this.activeIndex = (this.activeIndex - 1 + results.length) % results.length;
                    break;
                case 'Enter':
                    if (this.activeIndex > -1) {
                        event.preventDefault();
                        if (type === 'uni') {
                            const [name, id] = results[this.activeIndex];
                            this.selectUni(name, id);
                        } else {
                            const c = results[this.activeIndex];
                            this.selectCourse(c.course_code, c.course_id);
                        }
                    }
                    break;
                case 'Escape':
                    if (type === 'uni') this.showUniOpts = false;
                    else this.showCourseOpts = false;
                    this.activeIndex = -1;
                    break;
            }
        },

        handleBlur(elemName) {
            this.blurTimeout = setTimeout(() => {
                if (elemName == 'univ') this.showUniOpts = false;
                else if (elemName == 'course' && this.univID !== null) this.showCourseOpts = false;
                this.activeIndex = -1;
            }, 200);
        },

        shortenUniName(name) {
            if (!name) return '';
            return name
                .replace("University of California,", "UC")
                .replace("California State University,", "Cal State")
                .replace("California Polytechnic University,", "Cal Poly")
                .replace("State University", "State")
                .replace("San Luis Obispo", "SLO");
        },

        getCCName(cc_id) {
            return window.ccMap?.[cc_id] || `ID: ${cc_id}`
        }
    }));
});
