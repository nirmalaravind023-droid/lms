# Zero To LMS Learning Roadmap

User-facing note: many LMS screens now use the word `Section` even where the codebase still uses the backend model name `Course`.

## Who This Is For

This roadmap is for someone with:

- no coding background
- no web development background
- no idea what frontend, backend, database, or API means

The goal is to go from absolute beginner to someone who can:

- understand how an LMS works
- talk clearly with developers
- build simple LMS screens
- eventually build an LMS MVP

---

## Big Picture

Do **not** start with advanced topics like Kubernetes, Elasticsearch, microservices, or cloud scaling.

Start in this order:

1. HTML
2. CSS
3. JavaScript
4. Git and GitHub
5. React
6. TypeScript
7. Node.js
8. NestJS
9. PostgreSQL
10. Build LMS MVP

---

## Learning Path

### Phase 0: Computer and Web Basics
**Time:** 3 to 5 days

Learn:

- what a browser does
- what a website is
- what a web app is
- what frontend means
- what backend means
- what a database means
- what an API means

Outcome:

- You can explain how a learner opens a page, clicks a button, and data is saved.

Simple example:

`Learner opens page -> frontend shows course -> frontend calls backend -> backend reads database -> response comes back`

---

### Phase 1: HTML
**Time:** 1 to 2 weeks

Learn:

- headings
- paragraphs
- links
- images
- buttons
- forms
- input fields
- labels
- tables
- lists
- semantic tags like `header`, `main`, `section`, `footer`

Practice projects:

- login page
- learner dashboard page
- admin dashboard page
- quiz form page
- certificate preview page

Goal:

- Build static LMS pages with only HTML.

You are ready to move on when:

- you can create a full page layout without copying line by line
- you understand how forms and tables work

---

### Phase 2: CSS
**Time:** 2 weeks

Learn:

- colors
- spacing
- font size
- borders
- margin and padding
- flexbox
- grid
- responsive design
- hover states
- card layouts

Practice projects:

- style the login page
- create a learner dashboard with cards
- create an admin analytics layout
- create a department calendar mockup

Goal:

- Turn plain HTML into a clean UI.

You are ready to move on when:

- your pages look organized on desktop and mobile
- you can build sidebar + header + content layouts

---

### Phase 3: JavaScript
**Time:** 3 to 4 weeks

Learn:

- variables
- arrays
- objects
- functions
- conditions
- loops
- events
- DOM manipulation
- form validation
- local storage
- `fetch()` basics

Practice projects:

- login validation
- show/hide password
- quiz timer
- progress bar
- mark lesson complete button
- switch between course modules

Goal:

- Make your LMS pages interactive.

You are ready to move on when:

- you can update page content using JavaScript
- you understand how button clicks change UI state

---

### Phase 4: Git and GitHub
**Time:** 3 to 5 days

Learn:

- repository
- commit
- push
- pull
- branch
- merge

Goal:

- Save work safely and collaborate with developers.

Commands to know:

- `git init`
- `git status`
- `git add .`
- `git commit -m "message"`
- `git push`

---

### Phase 5: React
**Time:** 3 to 4 weeks

Learn:

- components
- props
- state
- events
- conditional rendering
- lists
- forms
- routing
- basic hooks

Practice projects:

- learner dashboard
- course list page
- course detail page
- quiz page
- admin course builder UI

Goal:

- Build reusable LMS screens instead of large HTML files.

You are ready to move on when:

- you can split a page into components
- you understand state and props clearly

---

### Phase 6: TypeScript
**Time:** 1 to 2 weeks

Learn:

- types
- interfaces
- optional fields
- arrays and object typing
- function typing

Why it matters:

- LMS apps have many roles, objects, and rules
- TypeScript helps reduce mistakes

Examples to type:

- `User`
- `Course`
- `Module`
- `Quiz`
- `Certificate`

Goal:

- Write safer frontend and backend code.

---

### Phase 7: Node.js and Backend Basics
**Time:** 2 weeks

Learn:

- what a server is
- what a request is
- what a response is
- REST API basics
- GET, POST, PUT, DELETE
- JSON
- authentication basics

Practice:

- create a simple API for courses
- create a login API
- create a progress API

Goal:

- Understand how the frontend talks to the server.

---

### Phase 8: NestJS
**Time:** 2 to 3 weeks

Learn:

- modules
- controllers
- services
- DTOs
- validation
- guards
- role-based access control

Build:

- auth module
- users module
- courses module
- progress module
- assessments module

Goal:

- Build a structured backend for an LMS.

---

### Phase 9: PostgreSQL and Database Design
**Time:** 2 to 3 weeks

Learn:

- tables
- rows
- primary keys
- foreign keys
- relationships
- indexes
- SQL basics

Main LMS tables to understand:

- companies
- departments
- users
- courses
- modules
- lessons
- enrollments
- progress
- assessments
- quiz attempts
- certificates
- messages

Goal:

- Understand how LMS data is stored and connected.

---

### Phase 10: LMS-Specific Features
**Time:** 3 to 4 weeks

Learn these one by one:

1. Authentication and roles
   - admin
   - HR/manager
   - learner

2. Multi-tenant logic
   - one company should not see another company's data

3. Course structure
   - course
   - module
   - submodule
   - lesson

4. Content types
   - video
   - article
   - PDF
   - mandatory reading

5. Progress tracking
   - not started
   - in progress
   - completed
   - overdue

6. Assessments
   - quiz
   - assignment
   - auto grading
   - manual grading

7. Certificates
   - eligibility
   - issue
   - revoke
   - reissue

8. Communication
   - direct messages
   - notifications

9. Analytics
   - average score
   - average time spent
   - not completed learners
   - department performance

---

## Recommended Mini Projects

Build these in order:

1. Static login page in HTML/CSS
2. Learner dashboard in HTML/CSS/JavaScript
3. Quiz page with timer in JavaScript
4. React course list and course details page
5. React admin dashboard
6. Simple Node.js API for courses
7. NestJS auth and user modules
8. PostgreSQL schema for users, courses, modules, progress
9. End-to-end LMS MVP

---

## LMS MVP To Build First

Do not build everything at once.

Build this MVP first:

- company login
- admin portal
- learner portal
- department assignment
- course/module/lesson management
- article, PDF, and video content
- mandatory reading checkbox
- quiz and score
- progress tracking
- basic reports
- certificate generation

Build later:

- automatic subtitles
- audio translation
- advanced analytics designer
- AI recommendations
- large-scale search

---

## Beginner-Friendly 6 Month Plan

### Month 1

- HTML
- CSS
- simple page building

### Month 2

- JavaScript basics
- DOM manipulation
- mini interactive pages

### Month 3

- React
- component thinking
- routing

### Month 4

- TypeScript
- Node.js basics
- API understanding

### Month 5

- NestJS
- PostgreSQL
- auth and CRUD

### Month 6

- build LMS MVP
- connect frontend, backend, and database
- add progress, quizzes, and certificates

---

## Daily Learning Routine

If you are self-learning, use this simple routine:

1. Learn one concept for 30 to 45 minutes.
2. Practice it for 60 minutes.
3. Build one small thing using it.
4. Write notes in simple language.
5. Repeat the next day.

Best rule:

- spend less time watching tutorials
- spend more time building small pages and features

---

## Tools To Use

- VS Code
- Google Chrome
- GitHub
- Node.js
- PostgreSQL
- Postman or Bruno

Later:

- React
- Vite
- NestJS
- Prisma
- Docker

---

## How To Know You Are Ready To Build The LMS

You are ready when you can explain:

- how login works
- how frontend and backend connect
- how course data is stored
- how learner progress is saved
- how admin sees reports
- how role-based access works

You do **not** need to know everything before starting.
You only need enough understanding to build the first version well.

---

## Final Advice

- Start simple.
- Learn by building.
- Do not chase too many technologies at the same time.
- For an LMS, strong basics matter more than trendy tools.
- HTML, CSS, JavaScript, React, Node.js, and PostgreSQL are enough to begin.

---

## Very Short Version

If you want the shortest possible roadmap:

`HTML -> CSS -> JavaScript -> Git -> React -> TypeScript -> Node.js -> NestJS -> PostgreSQL -> LMS MVP`
