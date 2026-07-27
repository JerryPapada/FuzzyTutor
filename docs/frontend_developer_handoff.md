# FuzzyTutor Frontend Developer Handoff

## 1. Current Frontend State

The current frontend is a Vite + React single-page tutor workspace in `frontend/src/main.jsx` with styling in `frontend/src/styles.css`.

It already implements:

- A usable first-screen learning workspace, not a marketing page.
- API health check display.
- Module list sidebar from `GET /api/learning/modules/`.
- Task catalog loading from `GET /api/learning/tasks/`.
- Module-local task filtering.
- MCQ rendering with radio choices.
- Code-task rendering with a textarea and starter code.
- Elapsed-time tracking per task.
- Manual Back/Forward task navigation.
- XAI sidebar showing:
  - `knowledgeMastery`
  - `systemCognitiveFriction`
  - `focusState`
  - `recommendation`
  - `supportMessage`

Important limitation: the current frontend submits directly to:

```text
POST /api/fuzzy/evaluate/
```

That endpoint is useful for standalone model demos, but it does **not** persist submissions, does **not** update learner sessions, does **not** store training data, and does **not** use backend next-task adaptation.

The frontend must now switch to the learning-session workflow.

## 2. Backend Features Now Available

The backend now supports:

- Anonymous learner sessions.
- Persistent task submissions.
- Fuzzy evaluation logs.
- Mamdani cognitive-friction model.
- Trained ANFIS mastery model.
- Backend next-task selection.
- A 105-task bank: 15 tasks per module and five per difficulty.
- Module-local mastery/friction and mastery-based exit after at least six attempts.
- Read-only review for skipped and incorrect attempts.
- Three server-persisted progressive hint levels per task.
- Micro-surveys every 5 submitted tasks.
- Training-data export.
- Swagger/OpenAPI docs.

Swagger:

```text
http://localhost:8000/api/docs/
http://localhost:8000/api/schema/
http://localhost:8000/api/redoc/
```

Main backend workflow:

```text
POST /api/learning/sessions/
GET  /api/learning/modules/
GET  /api/learning/tasks/
GET  /api/learning/sessions/<token>/review/
POST /api/learning/hints/
POST /api/learning/submissions/
POST /api/learning/micro-surveys/
```

## 3. Required Frontend Changes

### 3.1 Create and Store a Session

On app startup, create a learner session:

```http
POST /api/learning/sessions/
Content-Type: application/json

{}
```

Response shape:

```json
{
  "sessionToken": "abc123",
  "currentModuleId": 1,
  "currentTaskId": "lists-mcq-001",
  "aggregateMastery": 70.0,
  "aggregateFriction": 25.0,
  "completedTaskCount": 0,
  "latestRecommendation": "hold_current_tier",
  "surveyDue": false,
  "curriculumComplete": false,
  "submittedTaskIds": [],
  "skippedTaskIds": [],
  "orderedAttempts": [],
  "currentTask": {
    "id": "lists-mcq-001",
    "moduleId": 1,
    "type": "mcq",
    "difficulty": "foundation",
    "difficultyLevel": 1,
    "taskMetricWeight": 35,
    "baselineTimeSeconds": 55,
    "prompt": "..."
  },
  "hintState": {
    "revealedHints": [],
    "assistanceInteractions": 0,
    "maxHintLevel": 0,
    "nextLevel": 1,
    "exhausted": false
  },
  "moduleProgress": [
    {
      "moduleId": 1,
      "moduleMastery": 50.0,
      "moduleFriction": 25.0,
      "attemptedTaskCount": 0,
      "status": "active",
      "exitReason": null,
      "terminal": false,
      "completedAt": null
    }
  ]
}
```

`moduleProgress` contains one entry for each of the seven modules; the example shows only the active entry. `orderedAttempts` contains every persisted learner response in submission order, including correct MCQs and completed code tasks. It restores the learner's own answer after refresh but never exposes a private answer key. A populated item has this shape:

```json
{
  "taskId": "lists-mcq-001",
  "moduleId": 1,
  "skipped": false,
  "outcome": "correct",
  "learnerAnswer": {
    "selectedChoice": "Adds an item to the end"
  },
  "submittedAt": "2026-07-27T10:00:00+00:00"
}
```

Frontend state to add:

```js
const [session, setSession] = useState(null);
const [sessionToken, setSessionToken] = useState(null);
const [activeTask, setActiveTask] = useState(null);
const [surveyDue, setSurveyDue] = useState(false);
```

Store `sessionToken` in `localStorage` if persistence across refreshes is desired. If using localStorage, rehydrate by calling:

```text
GET /api/learning/sessions/<sessionToken>/
```

If that returns 404, create a new session.

### 3.2 Reveal Progressive Hints

The public task catalog never includes unrevealed hints. When the learner requests help, post:

```http
POST /api/learning/hints/
Content-Type: application/json

{
  "sessionToken": "abc123",
  "taskId": "lists-mcq-001",
  "elapsedTimeSeconds": 24.5
}
```

Each successful call reveals exactly one new level in order:

1. `conceptual`
2. `strategy`
3. `scaffold`

The response includes the newly revealed `hint` and the complete restorable `hintState`. Disable the hint button when `hintState.exhausted` is true. Session creation and restoration also return the current task's `hintState`.

### 3.3 Replace Direct Fuzzy Evaluation With Submission Flow

Current frontend behavior:

```text
POST /api/fuzzy/evaluate/
```

Required behavior:

```text
POST /api/learning/submissions/
```

Payload:

```json
{
  "sessionToken": "abc123",
  "taskId": "lists-mcq-001",
  "elapsedTimeSeconds": 42.5,
  "completionRatio": 1.0,
  "selectedChoice": "Adds an item to the end",
  "answerText": "",
  "answerPayload": {
    "clientTaskStartedAt": 1720000000000
  }
}
```

Do not send `assistanceInteractions`. The backend derives it from persisted hint events and rejects client-supplied values.

For MCQ:

- Send `selectedChoice`.
- Do not send `isCorrect`; the backend derives correctness from its private answer key.

For code tasks:

- Send `answerText`.
- Do **not** execute code in the frontend.
- Use completion behavior:
  - `completionRatio = 1` if the answer has meaningful content.
  - `completionRatio = 0` if empty.
  - Optionally use intermediate values later if the UI can detect partial progress.
- Do not send `isCorrect`. Code completion is behavioral evidence, not correctness or automated grading.

Response includes:

```json
{
  "knowledgeMastery": 92.81,
  "systemCognitiveFriction": 26.25,
  "focusState": "Needs Support",
  "recommendation": "increase_or_hold_high_tier",
  "supportMessage": "Keep the tier steady and add a short explanation.",
  "inputSnapshot": {},
  "engineTrace": {},
  "submissionId": 1,
  "session": {},
  "nextTask": {},
  "hintUsage": {
    "assistanceInteractions": 2,
    "maxHintLevel": 2,
    "revealedLevels": [1, 2]
  },
  "moduleDecision": {
    "moduleId": 1,
    "outcome": "continue",
    "attemptedTaskCount": 4,
    "moduleMastery": 72.4,
    "moduleFriction": 28.1,
    "minimumAttempts": 6,
    "recentMcqResults": [true, true],
    "recentMcqCorrectCount": 2,
    "masteryThresholdMet": false,
    "nextModuleId": null
  },
  "adaptation": {
    "direction": "increase",
    "targetDifficultyLevel": 2,
    "selectedDifficulty": "intermediate",
    "selectedScope": "module",
    "curriculumComplete": false,
    "reason": "High mastery with low friction supports a harder or equivalent task.",
    "signals": {
      "knowledgeMastery": 92.81,
      "systemCognitiveFriction": 26.25,
      "recommendation": "increase_or_hold_high_tier"
    }
  },
  "surveyDue": false
}
```

After submission:

- Set XAI panel from the response.
- Set `session` from `response.session`.
- Set `surveyDue` from `response.surveyDue`.
- Set the next active task from `response.nextTask`.
- Reset timer and answer state for the new task.

### 3.4 Use Backend-Selected Next Task

The backend now selects the next task according to model output:

```text
high mastery + low friction -> increase difficulty
low mastery or high friction -> decrease difficulty
mixed signals -> hold difficulty
```

Frontend should not decide adaptive difficulty itself.

The first six tasks in each module are balanced between MCQ and code. Starting with attempt six, the backend may return `moduleDecision.outcome = "mastery_exit"` when module mastery is at least 75, friction is below 40, and at least two of the latest three MCQs are correct. Otherwise the learner continues, with `"bank_exhausted"` after all 15 tasks. Display this as a calm completion message; do not calculate module completion in React.

The current Back/Forward buttons can remain as preview-only catalog browsing, but submissions must use the session's current backend-selected task. The primary learning flow should follow `nextTask` from `/api/learning/submissions/`. To begin a session from a previewed task, create a new session with that `taskId`.

Recommended UX:

- Primary button: `Submit response`
- After submission, update the task automatically to `nextTask`.
- Show a small adaptation line:

```text
Next: intermediate task
Reason: High mastery with low friction supports a harder or equivalent task.
```

Avoid exposing raw rule names as the main UI copy. They can be placed in an expandable "Model trace" section if needed.

### 3.5 Add Micro-Survey UI Every 5 Tasks

When `surveyDue` is true, show a compact modal or inline panel after the submission result. The backend keeps the oldest unanswered five-task milestone due across refreshes until a survey is accepted.

Endpoint:

```http
POST /api/learning/micro-surveys/
Content-Type: application/json
```

Payload:

```json
{
  "sessionToken": "abc123",
  "satisfactionScore": 4,
  "perceivedDifficulty": 3,
  "confidenceScore": 4,
  "comment": "Optional short text"
}
```

Required controls:

- `satisfactionScore`: 1 to 5
- `perceivedDifficulty`: 1 to 5
- `confidenceScore`: 1 to 5
- optional comment

Recommended UI:

- Use compact segmented controls or 1-5 buttons.
- Keep copy non-threatening.
- Do not block the whole app forever; allow submit and maybe a small skip action if desired.

Suggested labels:

```text
How was that task?
Satisfaction
Difficulty
Confidence
```

### 3.6 Show Richer XAI Information

Current XAI panel already shows the two main metrics.

Keep:

- Knowledge mastery gauge
- Cognitive friction gauge
- Focus state
- Recommendation/support message

Add:

- Adaptation reason from `response.adaptation.reason`
- Next selected difficulty from `response.adaptation.selectedDifficulty`
- Optional model mode indicator:
  - `response.engineTrace.anfis.modelType`
  - expected value after training: `trained_anfis`

Optional expandable details:

- ANFIS active rules:
  - `response.engineTrace.anfis.rules`
- Mamdani active rules:
  - `response.engineTrace.mamdani.rules`
- Defuzzification:
  - `response.engineTrace.mamdani.defuzzification`

Do not make the raw trace the main experience. The main UI should remain human-readable.

### 3.7 Add Read-Only Attempt Review

Load review material with:

```text
GET /api/learning/sessions/<sessionToken>/review/
GET /api/learning/sessions/<sessionToken>/review/?moduleId=1
```

The response contains only skipped tasks and incorrect MCQs. Each item includes the learner answer, outcome, revealed hints, private explanation, and either the MCQ `correctChoice` or code `answerGuide`. Render these in a read-only review panel. Do not show a retry or submit action; the backend rejects repeat submissions.

## 4. Current Backend Data Fields Useful for UI

Tasks now include:

```json
{
  "id": "arrays-code-001",
  "moduleId": 2,
  "type": "code",
  "difficulty": "intermediate",
  "difficultyLevel": 2,
  "taskMetricWeight": 55,
  "estimatedCognitiveLoad": "medium",
  "baselineTimeSeconds": 80,
  "prompt": "...",
  "conceptTags": ["array access", "indexing"],
  "adaptationSignals": {
    "masteryFeature": "taskMetricWeight",
    "frictionFeature": "relativeResponseTime",
    "trainingValue": "captures difficulty, timing, completion, assistance, and correctness context"
  }
}
```

Normal task responses never include `correctChoice`, `answerGuide`, `explanation`, or unrevealed `hints`. These fields appear only in eligible review items. Do not calculate correctness in the frontend.

Frontend should display:

- task type
- difficulty
- baseline time
- concept tags if there is space
- module progress

Frontend should not display:

- `taskMetricWeight` as a primary user-facing value
- raw training/adaptation metadata unless in a developer/debug panel

## 5. Suggested Refactor Plan

### Step 1: API Helper Layer

Create a small API helper module, e.g.:

```text
frontend/src/api.js
```

Functions:

```js
getHealth()
getModules()
getTasks()
createSession()
getSession(sessionToken)
getReview(sessionToken, moduleId)
revealHint(payload)
submitTask(payload)
submitMicroSurvey(payload)
```

This will keep `main.jsx` from becoming too tangled.

### Step 2: Session Bootstrap

On app load:

1. Fetch health/modules/tasks.
2. Load `sessionToken` from localStorage.
3. If token exists, call `GET /learning/sessions/<token>/`.
4. If not found, call `POST /learning/sessions/`.
5. Set active module/task from the session response.

### Step 3: Submission Flow

Replace `submitAnswer()` so it posts to `/learning/submissions/`.

Do not calculate `taskMetricWeight` in the frontend anymore. The backend derives it from the task catalog.

Keep frontend-calculated:

- elapsed time
- selected choice
- answer text
- completion ratio

### Step 4: Adapted Task Navigation

After submission:

```js
setEvaluation(response);
setSession(response.session);
setActiveModuleId(response.nextTask.moduleId);
setActiveTask(response.nextTask);
```

If the frontend continues using a task array/index, update the module index to match `nextTask.id`.

### Step 5: Micro-Survey

When `response.surveyDue === true`, show the micro-survey UI.

After successful survey submission:

```js
setSurveyDue(false);
```

The response also returns `milestoneTaskCount` and the updated `surveyDue`. A duplicate survey for the same milestone returns HTTP 400.

## 6. Acceptance Checklist

The frontend is ready when:

- App creates or restores a backend learner session.
- Hint requests reveal one persisted level at a time and restore after refresh.
- Module progress uses `session.moduleProgress`; mastery exits and bank exhaustion use `response.moduleDecision`.
- Skipped and incorrect attempts are available through a read-only review panel.
- Submissions go to `/api/learning/submissions/`, not `/api/fuzzy/evaluate/`.
- XAI panel still displays mastery, friction, focus state, recommendation, and support message.
- UI follows `response.nextTask` after each submission.
- Adaptation reason is visible in friendly language.
- Micro-survey appears every 5 submitted tasks.
- Code tasks are not sandbox-graded.
- Refresh does not immediately lose the learner session if localStorage is used.
- Swagger docs at `/api/docs/` provide typed request and response contracts matching the frontend workflow.

## 7. Example End-to-End Flow

Create session:

```bash
curl -X POST http://localhost:8000/api/learning/sessions/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

Reveal the next hint:

```bash
curl -X POST http://localhost:8000/api/learning/hints/ \
  -H "Content-Type: application/json" \
  -d '{
    "sessionToken": "SESSION_TOKEN_HERE",
    "taskId": "lists-mcq-001",
    "elapsedTimeSeconds": 24
  }'
```

Submit MCQ:

```bash
curl -X POST http://localhost:8000/api/learning/submissions/ \
  -H "Content-Type: application/json" \
  -d '{
    "sessionToken": "SESSION_TOKEN_HERE",
    "taskId": "lists-mcq-001",
    "elapsedTimeSeconds": 40,
    "completionRatio": 1,
    "selectedChoice": "Adds an item to the end"
  }'
```

Review skipped and incorrect attempts:

```bash
curl http://localhost:8000/api/learning/sessions/SESSION_TOKEN_HERE/review/
```

Submit micro-survey:

```bash
curl -X POST http://localhost:8000/api/learning/micro-surveys/ \
  -H "Content-Type: application/json" \
  -d '{
    "sessionToken": "SESSION_TOKEN_HERE",
    "satisfactionScore": 4,
    "perceivedDifficulty": 3,
    "confidenceScore": 4,
    "comment": "The support was clear."
  }'
```

## 8. Notes for Presentation

The frontend should make the AI state legible and calm:

- "Mastery" means readiness for the next concept.
- "Friction" means effort/strain, not failure.
- A learner can have high mastery and still need support.
- An adaptive increase can still include support if friction is mild.

This matches the backend behavior. For example, a response can produce:

```text
knowledgeMastery = 92.81
systemCognitiveFriction = 26.25
focusState = Needs Support
recommendation = increase_or_hold_high_tier
```

Meaning: the learner is ready to advance, but the UI should keep a short explanation or hint available.
