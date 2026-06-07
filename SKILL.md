---
name: chaoxing-teacher
description: Automate Chaoxing/Fanya teacher workflows for the SCUJCC portal with chaoxing_portal_tool.py. Use when the user says "进入超星", "超星", "查课程", "进入课程", "进入班级", "作业界面", "批改作业", "未批改作业", "给分", "提交分数", asks to save/login with cookies, or asks to grade Chaoxing homework. Supports API login, teaching-course selection, class selection, homework review bundles, content-aware scoring, score plan creation, score submission, and post-submit verification. Exam is currently disabled and should stay hidden.
---

# Chaoxing Teacher

Use the local tool in the cloned repository or skill directory:

```bash
python3 chaoxing_portal_tool.py ...
```

If `python3 chaoxing_portal_tool.py --help` fails because Python packages are missing, install the local requirements:

```bash
python3 -m pip install -r requirements.txt
```

Keep the interaction conversational. Do not expose cookies, passwords, or raw credential values. Do not submit scores unless the user explicitly confirms submission after seeing the final score summary.

## Current Scope

- Supported: API login, teaching courses, class selection, homework interface, ungraded homework discovery, submission extraction, content-aware scoring, score plan creation, score submission, post-submit verification.
- Disabled: exam workflows. If the user asks for exams, say the exam feature is currently hidden/disabled and continue with homework if relevant.
- The tool stores cookies in `.chaoxing_cookies.json`; never print cookie values.
- Browser opening is optional and needs `agent-browser`; API homework flows do not require opening a browser window.

## Conversation State

Carry forward the latest selected course, class, homework, review bundle, and grade plan in the conversation. If the user says "刚刚的班级", "第一个", or "提交分数", resolve it from the latest context instead of asking again.

If the requested action is ambiguous and a safe default exists, choose the default and show the result. Ask only when the next action could submit or change data.

## Login

When the user says "进入超星" or needs Chaoxing access:

```bash
python3 chaoxing_portal_tool.py api-status
```

If cookies are missing or expired, run:

```bash
python3 chaoxing_portal_tool.py login
```

The login command prompts for account and password. If a network command fails from sandbox restrictions, rerun it with the required network permission.

## Course And Class Flow

List only teaching courses:

```bash
python3 chaoxing_portal_tool.py courses
```

Show the user the teaching courses. Do not show student/learning courses.

After the user chooses a course:

```bash
python3 chaoxing_portal_tool.py course-classes "<course>"
```

Show classes and prioritize rows marked `[用户]`. After the user chooses a class, show available task choices:

```bash
python3 chaoxing_portal_tool.py task-options "<course>" "<clazz>"
```

Only homework should appear while exams are disabled. If opening the homework interface is useful:

```bash
python3 chaoxing_portal_tool.py course-task "<course>" "<clazz>" homework --open --headed
```

## Homework Discovery

For the selected course and class, find ungraded homework:

```bash
python3 chaoxing_portal_tool.py homework-ungraded "<course>" "<clazz>"
```

If none are returned, tell the user there is no ungraded homework for that class.

For a selected homework:

```bash
python3 chaoxing_portal_tool.py homework-submissions "<course>" "<clazz>" "<work>"
```

Use the homework index from `homework-ungraded` when the user says "第一个".

## Content Review Before Scoring

Before generating content-aware scores, create a review bundle:

```bash
python3 chaoxing_portal_tool.py homework-review-bundle "<course>" "<clazz>" "<work>" --download-assets --max-chars 8000 --no-auto-login
```

Inspect `reviews[].downloaded_assets[].extracted_text`, student answer text, filenames, image paths, and attachment metadata. Identify whether each submission matches the assigned homework. For document extraction failures, look at fallback extracted text, image assets, and attachment filename/context before deciding.

Scoring policy:

- Prefer scores at or above 70 when the submitted content is relevant and non-empty.
- Give below 70 only when there is a concrete content reason, such as irrelevant experiment, blank/missing work, invalid artifact, or no evidence of completing the assigned task.
- Every score should have a short reason.
- Random or normal distribution scoring is only a fallback when the user explicitly asks for non-content-based scoring or content is unavailable. It should not replace content review when extracted submissions are available.
- If the user gives a score range, treat it as the preferred band for relevant work, but allow justified exceptions for irrelevant or missing submissions.

Write a reviewed score JSON file with this shape:

```json
{
  "scores": [
    {
      "answer_id": "55478986",
      "student_name": "学生姓名",
      "score": 90,
      "content_summary": "提交内容摘要",
      "evidence": "评分依据",
      "reason": "给分理由"
    }
  ]
}
```

Then create a dry-run plan:

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed "<review_bundle.json>" "<review_scores.json>"
```

Show the final student score summary and reasons to the user. Stop before submission.

## Random Or Normal Distribution Fallback

Use only when the user explicitly wants random/normal scoring and does not require content review:

```bash
python3 chaoxing_portal_tool.py homework-grade-random "<course>" "<clazz>" "<work>" --score-range 70-95 --distribution normal
```

This is a dry run unless `--commit` is added. Prefer dry run first, show the saved plan, and wait for confirmation.

## Submission

Submit only after the user says an explicit command such as "提交分数".

```bash
python3 chaoxing_portal_tool.py homework-submit-plan "<grade_plan.json>" --commit --no-auto-login
```

After submission, report:

- submitted students and scores
- operation status/messages
- verification summary: expected, matched, mismatch, missing

If `mismatch` or `missing` is nonzero, surface the affected students immediately.

## Output Style

Use concise Chinese updates. Show choices as numbered lists when the user must choose. For final grading summaries, include student name, score, and brief reason. Keep operational command details out of the user-facing answer unless they help confirm what happened.

## Safety Boundaries

- Never print or repeat passwords or cookie values.
- Never submit scores without explicit confirmation.
- Never overwrite or rescore already submitted work unless the user clearly asks.
- Do not use browser/login fallback unless API login or cookie injection fails.
- Keep exam hidden until the user asks to resume its development.
