# Chaoxing Portal Tool

Target: `https://scujcc.fanya.chaoxing.com/portal`

## Quick start for a new environment

Run all commands from the directory that contains `chaoxing_portal_tool.py` and
`requirements.txt`.

Use the same Python executable for the whole flow. For example, if you start
with `python3.11 chaoxing_portal_tool.py doctor`, also use `python3.11` for
`setup`, `login`, and grading commands. If `python3` points to a broken Python,
switch to another working Python executable and keep using it.

Check whether the local environment is ready:

```bash
python3 chaoxing_portal_tool.py doctor
```

If dependencies are missing, install them into the local tool directory:

```bash
python3 chaoxing_portal_tool.py setup
```

`setup` installs packages into a Python-version-specific directory under
`.chaoxing_deps/` next to this script. It avoids modifying the system Python
environment.

If `setup` fails because pip cannot start, repair/reinstall that Python or use a
different working Python executable, then rerun `doctor` and `setup` with that
same executable.

Check again:

```bash
python3 chaoxing_portal_tool.py doctor
```

Then log in if needed:

```bash
python3 chaoxing_portal_tool.py login
```

To verify saved cookies too:

```bash
python3 chaoxing_portal_tool.py doctor --check-login
```

After login, immediately list teacher courses and enter the course-selection
flow instead of stopping at the login success message:

```bash
python3 chaoxing_portal_tool.py courses
```

Browser commands are optional and require `agent-browser`. The API homework
workflow does not require a browser window.

## API login

```bash
python3 chaoxing_portal_tool.py login
```

The command prompts for account and password, calls Chaoxing/Fanya's
`/fanyalogin` HTTP API, and saves cookies here:

```text
.chaoxing_cookies.json
```

When the agent UI does not expose a usable stdin prompt, use macOS secure input
dialogs while still logging in through the HTTP API:

```bash
python3 chaoxing_portal_tool.py login --macos-dialog
```

As an explicit fallback, `--stdin-json` reads credentials from stdin. Use this
only after the user accepts that the password may enter the chat or caller
context. The command does not print the password.

```bash
python3 chaoxing_portal_tool.py login --stdin-json
```

stdin payload:

```json
{"username":"...", "password":"..."}
```

You can also provide credentials through environment variables:

```bash
CHAOXING_USERNAME=... CHAOXING_PASSWORD=... \
  python3 chaoxing_portal_tool.py login
```

## Check saved cookies

```bash
python3 chaoxing_portal_tool.py api-status
```

If the saved cookies are missing or expired, the command prompts for account
and then password, logs in through the API, and saves fresh cookies.

## Open with saved cookies

```bash
python3 chaoxing_portal_tool.py open --headed
```

Before opening the portal, this injects the saved API cookies into the
`agent-browser` session. If the cookies are missing or expired, it prompts for
account and password first.

## Exam question drafting

Generate a local exam-question draft from course content files. This does not
create, import, or publish an online Chaoxing exam.

```bash
python3 chaoxing_portal_tool.py exam-question-draft lecture.md \
  --title "第 3 章测试题" \
  --course 人工智能原理 \
  --chapter "搜索算法" \
  --knowledge-points "状态空间,A*算法,启发式函数" \
  --count 12 \
  --types single_choice,multiple_choice,true_false,short_answer \
  --markdown-output exam_questions_review.md
```

Supported source files:

- `.txt`, `.md`, `.html`
- `.docx`, `.pdf` when the optional extraction packages are available
- `.json`, including review/content bundles, but cookie files are refused
- `-` for stdin

Useful type names:

- `single_choice` / `单选题`
- `multiple_choice` / `多选题`
- `true_false` / `判断题`
- `short_answer` / `简答题`
- `essay` / `论述题`

The JSON draft is saved under `.chaoxing_question_drafts/` by default. Add
`--output path.json` to choose a specific JSON path, or `--format markdown` to
print a Markdown review copy. All generated questions are marked as drafts and
should be reviewed by the teacher before any platform import.

## Teaching courses

List only courses taught by the logged-in user:

```bash
python3 chaoxing_portal_tool.py courses
```

Infer the task from the user's original request. If they said "使用超星批改作业",
"批改作业", or "给分", keep the intended task as 批改作业. If they said
"使用超星新建考试", "新建考试", "考试出题", or "生成试题", keep the intended task
as 新建考试.

After the user selects a course, use the stored task directly. Ask for the next
task before listing classes only when the original request did not make it
clear:

1. 批改作业
2. 新建考试

For 批改作业, show classes for the selected teaching course:

```bash
python3 chaoxing_portal_tool.py course-classes 人工智能原理
```

For 新建考试, open the online exam page first. Chaoxing's exam URL still needs a
class context, so use the first clearly marked `[用户]` class when available, or
ask the user to choose a class if no user class is known.

```bash
python3 chaoxing_portal_tool.py course-task 人工智能原理 1 exam --open --headed
```

After opening the page, inspect it with `agent-browser snapshot -i -u -d 5` and
confirm that the "新建考试" button is visible. Do not click the button until the
user explicitly asks to proceed. Use `exam-question-draft` later when preparing
question content.

Show classes for a selected teaching course:

```bash
python3 chaoxing_portal_tool.py course-classes 人工智能原理
```

The class list auto-detects the current account name and prioritizes classes
whose names contain that user name, marking them with `[用户]`.

This is the non-interactive homework flow intended for LLM use: the model
preserves the user's intended task, lists teaching courses in chat, and after
the user picks a course either calls `course-classes` directly for 批改作业 or
opens the exam page for 新建考试. It asks whether to 批改作业 or 新建考试 only when
the original request did not say.

## Selected class tasks

After the user selects a class, show the task choices for that same class.
Exam and homework entries can be shown. Opening the exam page is allowed; exam
creation/publishing actions still require explicit user confirmation and a
separate implemented flow.

```bash
python3 chaoxing_portal_tool.py task-options 人工智能原理 142468056
```

The class argument can be the displayed class index, a class name/partial name,
or `clazz_id`.

Enter the selected class's homework interface:

```bash
python3 chaoxing_portal_tool.py course-task 人工智能原理 142468056 homework
```

Use `--open --headed` to open the generated interface in a visible browser:

```bash
python3 chaoxing_portal_tool.py course-task 人工智能原理 142468056 homework --open --headed
```

For LLM orchestration, the intended flow is:

1. `courses`
2. `course-classes <course>`
3. `task-options <course> <clazz>`
4. `course-task <course> <clazz> homework`

## Homework grading flow

List homework items in the selected class that still have pending submissions:

```bash
python3 chaoxing_portal_tool.py homework-ungraded 人工智能原理 142468056
```

List pending submissions for a selected homework. The homework argument can be
the index shown by `homework-ungraded`, a title/partial title, or `work_id`.

```bash
python3 chaoxing_portal_tool.py homework-submissions 人工智能原理 142468056 1
```

Review a pending submission. If the answer contains images or attachments, the
command prints their URLs/metadata; add `--open --headed` to open the full
review page.

```bash
python3 chaoxing_portal_tool.py homework-review 人工智能原理 142468056 1 1
```

For LLM-assisted grading, extract a review bundle before generating scores:

```bash
python3 chaoxing_portal_tool.py homework-review-bundle 人工智能原理 142468056 1 --download-assets
```

The bundle includes student answer text, answer images, downloaded student
attachments, and extracted document text when supported. When `--download-assets`
is used, answer images are saved locally and referenced by path in
`downloaded_assets`; the model should inspect those image paths along with
extracted text, filenames, and attachment metadata before suggesting scores.
Suggested scores should normally stay at or above 70. Scores below 70 require a
concrete reason such as blank submission, irrelevant content, missing required
artifacts, or clearly invalid work.

After the model has reviewed the extracted content, write a JSON score file:

```json
{
  "scores": [
    {
      "answer_id": "55478986",
      "score": 90,
      "reason": "内容与实验主题匹配，流程完整。",
      "evidence": "报告包含 KNN、鸢尾花数据集、K 值对比和准确率分析。"
    }
  ]
}
```

Then convert the reviewed scores into a dry-run grade plan:

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed .chaoxing_review_bundles/review_bundle_...json reviewed_scores.json
```

The generated plan is not submitted. Show its final student score summary to
the user and wait for explicit confirmation.

Generate random scores for pending submissions. This is a dry run unless
`--commit` is explicitly provided. The dry run saves the exact score plan to
`.chaoxing_grade_plans/` so the model can show the final student score summary
and only submit that same plan after the user confirms.

```bash
python3 chaoxing_portal_tool.py homework-grade-random 人工智能原理 142468056 1 --score-range 80-90
python3 chaoxing_portal_tool.py homework-grade-random 人工智能原理 142468056 1 --score-range 80-90 --distribution normal
python3 chaoxing_portal_tool.py homework-submit-plan .chaoxing_grade_plans/grade_plan_...json --commit
```

`homework-submit-plan --commit` submits the exact saved scores and then fetches
the mark list again to verify that the actual page scores match the plan.

## Browser fallback

```bash
python3 chaoxing_portal_tool.py browser-login
```

Use this only when the API flow requires captcha, SMS, QR, or two-factor
verification.

## Clear saved cookies/state

```bash
python3 chaoxing_portal_tool.py clear
```
