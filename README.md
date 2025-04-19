# CACourses

**A tool for CA students to find the perfect course replacement.**

Welcome to my little passion project! I've been working on this on and off for around a year now. Little bursts of motivation push me through, and every time I return I realize why I despise web development so much. Maybe its just the nature of the messy data and various services, or maybe its the lack of documentation for an API that's not designed for (but not barred from) public use. Either way, I'd like to share my vision for this project and update this README as it goes.

## Roadmap

- [x] Generate a local sqlite version of our production DB with 2 tables: a course glossary and articulation table.
  - [x] Generate course glossary in-memory
  - [x] Generate articulation table in-memory
  - [x] Write tables to sqlite db
- [x] Write backend functions to query sqlite db
- [ ] Add functionality to frontend
  - [ ] Improve/fix dropdown logic & ensure its mobile friendly
  - [ ] Parse backend json into basic cells
- [x] Port backend functions to AWS lambda & DB to supabase postgres
- [ ] Collaborate with frontend dev for better frontend
- [ ] Ensure request limits / basic security in place & release

### Current Challenges

- frontend parsing of return json
- better handling of list items from courses request
- security security security please dont spam my lambda endpoints

## The Vision

Have you ever had to take this one class or set of classes at your home university that you *really* wish you didn't have to take there? Would you prefer different professors, a different time slot, online learning, or smaller class sizes? Are you trying to take classes over summer to progress in your degree without paying the exorbitant per-credit fees associated with UC or CSU?

Answers to those questions often lead one to the following solution: **California Community Colleges**. CCs are much cheaper in comparison with classes being only $46/unit and have a variety of online options. There's an issue though- **You need to make sure your university will accept your community college class.** To do that, you need to ensure there's an agreement in place between both institutions to give you credit for, let's say, MATH19A at UCSC for MATH150 at SD Miramar College.

Enter [ASSIST.org](https://assist.org): a fantastic tool developed in partnership with UC, CSU, and the California CC system to allow prospective CC transfers to ensure they meet their course requirements. You can input your CC and target university then view every course mapping from a CC course to its university equivalent. Conveniently, this allows students who want a replacement course to pick their home university and a CC of interest and check for the presence of a course.

One small issue: You need to check each community college for articulations seperately, and the time adds up. Fast. It would be *pretty nice* if there was a tool where we could just pick our university, pick which course we wanted to replace, and get a list of all of our possible alternatives.

Enter CACourses: the tool which provides exactly that.

## Files

- `data/institutions_cc.json`: mapping between IDs seen in ASSIST urls to names of California CCs
- `data/institutions_state.json`: mapping between IDs seen in ASSIST urls to names of California public 4-year universities
- `download_data.py`: Python script to asynchronously download local copy of ASSIST data, will likely be adapted for periodic DB updates
- `index.html`: concept mock-up of front-end UI html, will likely be revamped
- `style.css`: concept mock-up of front-end UI css, will likely be revamped
- `test.ipynb`: primary testing space to develop functions for parsing ASSIST data into DB
- `.gitignore`: list of files for git to ignore

### Hidden Files

- `data/*/*`: not seen, local copy of all AY '24-'25 assist agreements in JSON format
- `test-data/`: not seen, other JSON files mainly used for exploratory analysis of the API
