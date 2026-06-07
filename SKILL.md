---
name: chaoxing-teacher
description: Automate Chaoxing/Fanya teacher workflows with chaoxing_portal_tool.py. Use this skill whenever the user mentions "超星", "学习通", "泛雅", "进入课程", "进入班级", "作业界面", "批改作业", "未批改作业", "给分", "提交分数", saving cookies, logging in, listing teacher courses, extracting homework submissions, or grading Chaoxing homework. It includes first-run setup/doctor checks, local dependency installation, API login, teaching-course and class selection, homework review bundles with images/attachments, content-aware scoring, explicit confirmation before submission, and post-submit verification. Exam workflows are disabled and should stay hidden.
---

# Chaoxing Teacher

Use `chaoxing_portal_tool.py` from the directory that contains this `SKILL.md`, `chaoxing_portal_tool.py`, and `requirements.txt`.

```bash
python3 chaoxing_portal_tool.py ...
```

Keep the interaction conversational and beginner-friendly. Explain what the next step does in plain Chinese, but do not expose cookies, passwords, or raw credential values. Do not submit scores unless the user explicitly confirms submission after seeing the final score summary.

## First Run In Any Environment

Start every unfamiliar environment with:

```bash
python3 chaoxing_portal_tool.py doctor
```

If required Python packages are missing, run:

```bash
python3 chaoxing_portal_tool.py setup
```

`setup` installs packages from `requirements.txt` into the local `.chaoxing_deps/` directory next to the tool. It does not install into the system Python environment and does not require the user to understand virtual environments.

After setup, run:

```bash
python3 chaoxing_portal_tool.py doctor
```

To also verify saved Chaoxing login cookies:

```bash
python3 chaoxing_portal_tool.py doctor --check-login
```

If login is missing or expired, run:

```bash
python3 chaoxing_portal_tool.py login
```

The `login` command prompts for account and password, saves only cookies in `.chaoxing_cookies.json`, and should not print secret values. If a network command fails because of sandbox/network restrictions, rerun that command with the required permission.

## Current Scope

- Supported: first-run setup checks, API login, teaching courses, class selection, homework interface, ungraded homework discovery, submission extraction, content-aware scoring, score plan creation, score submission, and post-submit verification.
- Disabled: exam workflows. If the user asks for exams, say the exam feature is currently hidden/disabled and continue with homework if relevant.
- Browser opening is optional and needs `agent-browser`; API login and homework grading flows do not require opening a browser window.
- Runtime data stays local and should not be committed or printed: `.chaoxing_cookies.json`, `.chaoxing_review_bundles/`, `.chaoxing_grade_plans/`, and `.chaoxing_deps/`.

## Conversation State

Carry forward the latest selected course, class, homework, review bundle, and grade plan in the conversation. If the user says "刚刚的班级", "第一个", or "提交分数", resolve it from the latest context instead of asking again.

If the requested action is ambiguous and a safe default exists, choose the default and show the result. Ask only when the next action could submit or change data.

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

Inspect `reviews[].summary.student_answers[].text`, `reviews[].summary.answer_images`, `reviews[].downloaded_assets[].path`, `reviews[].downloaded_assets[].extracted_text`, filenames, and attachment metadata. When `--download-assets` is used, answer images are downloaded locally and referenced by path; attachments are downloaded and text is extracted when supported. Use the image paths and extracted text as grading evidence when available.

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
