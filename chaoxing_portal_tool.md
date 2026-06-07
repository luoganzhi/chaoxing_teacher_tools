# Chaoxing Portal Tool

Target: `https://scujcc.fanya.chaoxing.com/portal`

## API login

```bash
python3 chaoxing_portal_tool.py login
```

The command prompts for account and password, calls Chaoxing/Fanya's
`/fanyalogin` HTTP API, and saves cookies here:

```text
.chaoxing_cookies.json
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

## Teaching courses

List only courses taught by the logged-in user:

```bash
python3 chaoxing_portal_tool.py courses
```

Show classes for a selected teaching course:

```bash
python3 chaoxing_portal_tool.py course-classes 人工智能原理
```

The class list auto-detects the current account name and prioritizes classes
whose names contain that user name, marking them with `[用户]`.

This is the non-interactive flow intended for LLM use: the model lists teaching
courses in chat, the user says which course to enter, and the model calls
`course-classes` to show the class list.

## Selected class tasks

After the user selects a class, show the task choices for that same class.
Exam is currently hidden until that workflow is finished, so only homework is
shown.

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
attachments, and extracted document text when supported. The model should
inspect that content before suggesting scores. Suggested scores should normally
stay at or above 70. Scores below 70 require a concrete reason such as blank
submission, irrelevant content, missing required artifacts, or clearly invalid
work.

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
