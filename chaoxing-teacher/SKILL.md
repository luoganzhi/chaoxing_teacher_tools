---
name: chaoxing-teacher
description: Automate Chaoxing/Fanya teacher workflows with chaoxing_portal_tool.py and agent-browser. Use this skill whenever the user mentions "超星", "学习通", "泛雅", "进入课程", "进入班级", "作业界面", "批改作业", "未批改作业", "给分", "提交分数", "考试出题", "生成试题", "根据内容出题", "期末复习", "提高通过率", "试卷草稿", "新建考试", "试卷库", "在线试卷库", "手动创建试卷", saving cookies, logging in, listing teacher courses, extracting homework submissions, grading Chaoxing homework, drafting exam questions from course content or final-exam reference papers, or creating/importing teacher-side online paper-library exam drafts. It includes first-run setup/doctor checks, API login, teaching-course and class selection, homework grading, and safe online paper-library draft creation for review/consolidation papers. Never publish exams or submit scores unless the user explicitly confirms.
---

# Chaoxing Teacher

Use `chaoxing_portal_tool.py` from the directory that contains this `SKILL.md`, `chaoxing_portal_tool.py`, and `requirements.txt`.

```bash
python3 chaoxing_portal_tool.py ...
```

Use the same Python executable for `doctor`, `setup`, `login`, and grading commands in a given environment. If `python3` points to a broken Python, switch to another working Python such as `python3.11` and keep using that same executable.

Keep the interaction conversational and beginner-friendly. Explain what the next step does in plain Chinese, but do not expose cookies, passwords, or raw credential values. Do not submit scores or publish exam content unless the user explicitly confirms after seeing the final summary.

## First Run In Any Environment

Start every unfamiliar environment with:

```bash
python3 chaoxing_portal_tool.py doctor
```

If required Python packages are missing, run:

```bash
python3 chaoxing_portal_tool.py setup
```

`setup` installs packages from `requirements.txt` into a Python-version-specific directory under `.chaoxing_deps/` next to the tool. It does not install into the system Python environment and does not require the user to understand virtual environments.

If `setup` fails because the Python executable's own `pip` is broken, tell the user this is an environment/Python installation problem, not a Chaoxing login problem. Use another working Python executable and rerun the same flow with that executable.

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

If the current agent UI cannot provide a real stdin prompt or secure password input, prefer:

```bash
python3 chaoxing_portal_tool.py login --macos-dialog
```

Only if the user explicitly asks to provide the password through the agent conversation and accepts that the password may enter the chat context, use the opt-in stdin JSON flow. Do not print the JSON, do not echo the password, and do not save it anywhere except the resulting cookie file:

```bash
python3 chaoxing_portal_tool.py login --stdin-json
```

Pass stdin as:

```json
{"username":"...", "password":"..."}
```

Infer and store the intended task from the user's original request before login:

- If the user says "使用超星新建考试", "新建考试", "考试出题", "生成试题", "根据内容出题", or "试卷草稿", set intended task to 新建考试.
- If the user says "使用超星批改作业", "批改作业", "未批改作业", "给分", "提交分数", or "批阅作业", set intended task to 批改作业.
- If neither intent is clear, leave intended task unset and ask after course selection.

After any successful login or cookie refresh, immediately continue to the course-selection flow by running:

```bash
python3 chaoxing_portal_tool.py courses
```

Show the teaching course list and ask the user which course to enter. Do not stop at "登录成功" unless the user only asked to verify login status. Keep the inferred intended task while asking for the course.

## Current Scope

- Supported: first-run setup checks, API login, teaching courses, class selection, opening the online exam page, safe online paper-library draft creation, final-review/consolidation paper generation from provided期末测试题 or reference papers, reusable Chaoxing import packaging/validation, Word smart import into manually created papers, local exam-question draft generation from content files, homework interface, ungraded homework discovery, submission extraction, content-aware scoring, score plan creation, score submission, and post-submit verification.
- Disabled by default: publishing or releasing exams to students, changing live exam settings, and submitting scores. Creating and saving papers in the teacher-side paper library is allowed when the user explicitly asks for 新建考试/创建试卷/提交试卷, because it does not publish to students.
- Browser opening is optional and needs `agent-browser`; API login and homework grading flows do not require opening a browser window.
- Runtime data stays local and should not be committed or printed: `.chaoxing_cookies.json`, `.chaoxing_review_bundles/`, `.chaoxing_grade_plans/`, `.chaoxing_question_drafts/`, and `.chaoxing_deps/`.

## Conversation State

Carry forward the latest selected course, intended task (批改作业 or 新建考试), class, homework, review bundle, grade plan, source content file, exam-question draft, browser session name, paper folder, and current paper id in the conversation. If the user says "刚刚的班级", "第一个", "继续根据这个内容出题", "继续", or "提交分数", resolve it from the latest context instead of asking again.

If the requested action is ambiguous and a safe default exists, choose the default and show the result. Ask only when the next action could submit or change data.

## Course And Task Flow

List only teaching courses:

```bash
python3 chaoxing_portal_tool.py courses
```

Show the user the teaching courses. Do not show student/learning courses. If this command follows a successful login, present it as the next step automatically instead of waiting for another user prompt.

After the user chooses a course, branch based on the stored intended task:

- If intended task is 批改作业, immediately list classes for that course.
- If intended task is 新建考试, enter the exam page flow. Choose a reasonable default user class if one is clearly marked `[用户]`, otherwise ask which class to use for opening the exam page.
- If intended task is unset, ask what they want to do before listing classes:

1. 批改作业
2. 新建考试

If the user chooses or already requested 批改作业, then list classes:

```bash
python3 chaoxing_portal_tool.py course-classes "<course>"
```

Show classes and prioritize rows marked `[用户]`. After the user chooses a class, show homework task choices:

```bash
python3 chaoxing_portal_tool.py task-options "<course>" "<clazz>"
```

Homework and exam page entries may appear. Online exam creation/publishing is still disabled, but opening the exam page for inspection is allowed. If opening the homework interface is useful:

```bash
python3 chaoxing_portal_tool.py course-task "<course>" "<clazz>" homework --open --headed
```

If the user chooses or already requested 新建考试, open the exam page and inspect it. A class context is required by Chaoxing URLs; if the latest class list has a `[用户]` class, use the first `[用户]` class as the default and tell the user which class was used. Otherwise ask the user to choose a class.

```bash
python3 chaoxing_portal_tool.py course-task "<course>" "<clazz>" exam --open --headed
```

After opening, use `agent-browser snapshot -i -u -d 5` on the same browser session to confirm whether the "新建考试" button is visible. Report the button ref if visible. Do not click "新建考试" until the user explicitly asks to proceed.

Use local `exam-question-draft` when the user asks only to prepare questions/content for review. Use the online paper-library workflow below when the user asks to create/import/save papers in Chaoxing, including final-review papers generated from supplied期末测试题 or sample exams.

## Exam Question Drafting

When the user asks for "考试出题", "根据内容出题", "生成试题", "期末复习", "提高通过率", or "试卷草稿", first clarify or infer the source content. Good sources include `.txt`, `.md`, `.html`, `.docx`, `.pdf`, and `.json` files. Do not use cookie files, grade plans, or private runtime files as source content.

Generate a local exam-question draft:

```bash
python3 chaoxing_portal_tool.py exam-question-draft "<source_file>" --title "考试题草稿" --count 10 --types single_choice,true_false,short_answer --markdown-output "<review.md>"
```

Useful options:

- `--types single_choice,multiple_choice,true_false,short_answer,essay`
- `--course "<course_name>"`
- `--chapter "<chapter_name>"`
- `--knowledge-points "知识点1,知识点2"`
- `--format json` when the next step needs structured data

The generated JSON is saved under `.chaoxing_question_drafts/` unless `--output` is provided. Show the draft file path and a concise question summary. Make clear that the draft is not published to Chaoxing and needs teacher review before import or publishing.

If the user asks to create or import the online paper-library draft, follow the next section. If the user asks to publish/release the exam to students, stop and ask for explicit confirmation after summarizing the papers and target class.

## Online Paper-Library Exam Creation

Use this workflow when the user says "新建考试", "提交试卷", "把试卷放到超星", "使用超星新建考试", "手动创建", "Word 智能导入", "在线试卷库", or asks to create/import papers in the Chaoxing paper library. This is also the default workflow when the user provides期末测试题/reference papers and asks to generate practice papers for student final review inside Chaoxing.

Safety boundary:

- Creating and saving papers in the teacher-side 试卷库 is allowed after the user asks for it.
- Do not publish/release/fafang exams to students, change live exam settings, or start an exam unless the user gives a separate explicit confirmation.
- Tell the user final output is "保存到试卷库，未发布给学生".

### Required Browser Flow

Use `agent-browser` for the web UI. Prefer a stable session name such as `chaoxing-exam-check` so refs and login state persist.

1. Open the course exam page with:

   ```bash
   python3 chaoxing_portal_tool.py course-task "<course>" "<clazz>" exam --open --headed
   ```

2. Use snapshots to enter the paper library/exam page. Click `新建考试` only after the user has asked to create an exam/paper.
3. In the create modal, choose `手动创建试卷`, then `下一步`.
4. In the editor, use `智能导入` -> `Word 智能导入`.
5. Before upload, package and validate the import text with the bundled helper instead of writing a one-off script:

   ```bash
   python3 scripts/chaoxing_import_packager.py "<import_txt>" --output-dir ".chaoxing_question_drafts" --expected-score 100
   ```

   Read the summary and `.validation.json`. Fix all `ERROR` issues before upload. Treat warnings about isolated `A/B/C/D` tokens in stems as likely Chaoxing smart-import risks.
6. Upload the prepared `.docx` through the hidden `#file` input:

   ```bash
   agent-browser --session chaoxing-exam-check upload '#file' "<docx_path>"
   ```

7. Wait for `共识别 ... 题，其中识别有误 0 题`.
8. Click `加入试卷`, then the returned `确定`.
9. Fill the title textbox with the requested paper name, click `完成`, then confirm `确定`.
10. Verify the paper appears in the intended folder with the expected 题量 and 总分.

If an already-created paper needs content fixes, use the editor URL:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/exam/create-exampaper?courseid=<courseid>&paperid=<paperid>&cpi=<cpi>&ut=t&qbanksystem=0&qbankbackurl=&courseIdsStr=&groupId=0&linkFrom=
```

For single choice questions, the page editor uses `/mooc2-ans/exam/editPaperSingleChoiceV2`. When editing via JavaScript, update `content`, `A`-`D`, and `defAnswer` together. Validate by reading `/mooc2-ans/exam/viewLibraryRelationQuestionDetail`.

For true/false questions, the page editor uses `/mooc2-ans/exam/editPaperTrueFalseV2`. Use `answer: "true"` for 对 and `answer: "false"` for 错.

### Paper Folder Naming

When the user asks to put generated papers in a folder, match the visible naming style of existing folders. If the teacher name is available, prefer:

```text
<教师名>-测试
```

For the current teacher account this may look like `罗淦之-测试`. Create the folder before moving/creating papers when possible. If papers are created outside the folder, select them and use batch `移动到` to move them into the folder.

### Paper Naming

If the user asks for generic names, use exactly:

```text
测试1
测试2
测试3
```

Do not use long source-file names unless the user explicitly asks.

### Generating Similar Papers From Reference Exams

When asked to generate several papers from reference papers:

- Treat the teaching goal as期末复习巩固: help students practice high-frequency tested concepts, common mistake points, and exam-like drills to improve passing probability.
- If the user asks to put the generated papers into Chaoxing, create/import them through the online paper-library workflow above, not as only local files.
- Preserve the tested knowledge points and difficulty. By default, target about 90% conceptual similarity to the reference papers.
- Do not over-diversify beyond the reference unless the user asks; the papers should feel exam-adjacent while avoiding exact copying.
- Avoid making papers look like direct copies. Change surface form:
  - shuffle question order within each objective-question section;
  - shuffle single-choice option order;
  - recompute the correct answer letter after shuffling options;
  - lightly rewrite stems while preserving the tested concept;
  - keep numeric/computational questions logically equivalent unless the user asks to change numbers.
- Always include an answer blank in single-choice stems, normally `（  ）`.
- First and second papers may be objective-only if the user says "不需要主观题/简答与应用"; increase single-choice/true-false counts to keep 100 points.
- The third paper should keep the original exam structure when the user says "尽量和考试一样"; only change wording, order, option order, and safe numbers.
- Keep total score at 100 unless the user asks otherwise.
- Keep answers and scoring rubrics in the source/import files for teacher review, but do not expose sensitive account/cookie data.

Write local artifacts under `.chaoxing_question_drafts/`:

```text
<paper-draft>.md          # teacher review copy
chaoxing_import_<id>.txt  # import text
chaoxing_import_<id>.docx # Word smart import file
chaoxing_import_<id>.validation.json # helper validation report
```

For `.docx` creation, use the bundled helper from this skill directory:

```bash
python3 scripts/chaoxing_import_packager.py "<import_txt>" --output-dir ".chaoxing_question_drafts" --expected-count <n> --expected-score 100
```

The helper validates the import text, writes a `.validation.json` report, and creates the `.docx`. Do not create throwaway `/private/tmp` packaging scripts for this conversion; if deterministic packaging behavior is missing, improve the bundled helper.

### Known Chaoxing Smart-Import Pitfalls

- Single-choice stems must include a visible Chinese answer blank such as `（  ）`; do not rely on an empty ASCII `()`.
- Avoid isolated option-like tokens `A`, `B`, `C`, or `D` inside stems because Chaoxing may split them as options. Rewrite placeholders as `甲/乙/丙/丁`, `指标一/指标二`, or similar Chinese markers.
- After option shuffling, recompute the answer letter from the shuffled option order before packaging.
- If smart import reports a wrong type count or `识别有误` is nonzero, stop, clear the import page, fix the source text, regenerate the `.docx`, upload again, and recheck before clicking `加入试卷`.

### Chaoxing Import Text Format

Use this import style for single-choice questions:

```text
【单选题】1. 题干中的答案空位是（  ）。（2分）
A. 选项A
B. 选项B
C. 选项C
D. 选项D
答案：B
```

Use this import style for true/false:

```text
【判断题】1. 判断题题干。（2分）
答案：√
```

Use this import style for fill-in blanks:

```text
【填空题】1. Transformer的核心模块之一是多头 ______ 机制。（2分）
答案：注意力
```

Use this import style for short-answer/application questions:

```text
【简答题】1. 简述问题。（6分）
答案：参考答案。
解析：评分标准。
```

### Verification Checklist

Before final response, verify and report:

- folder name;
- paper names;
- question count and total score for each paper;
- single-choice stems include `（ ）`;
- the helper validation report has no `ERROR` entries;
- single-choice options and answer letters were shuffled/recomputed;
- true/false order was adjusted when applicable;
- recognition result was `识别有误 0 题` if importing;
- papers are saved in paper library and not published to students.

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
- Do not ask for a password in ordinary chat unless the user explicitly requests conversation-based password entry and accepts the exposure risk.
- Never submit scores without explicit confirmation.
- Never overwrite or rescore already submitted work unless the user clearly asks.
- Do not use browser/login fallback unless API login or cookie injection fails.
- Keep exam hidden until the user asks to resume its development.
