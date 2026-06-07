# Chaoxing Teacher Tools

超星/泛雅教师端本地辅助工具，用于让 agent 稳定完成教师课程查询、班级选择、作业内容提取、辅助评分、提交前确认和提交后验证。

目标入口：`https://scujcc.fanya.chaoxing.com/portal`

## What This Does

- 检查当前环境是否可用
- 本地安装 Python 依赖，不污染系统环境
- 登录超星并保存本地 cookie
- 只列出教师课程和班级
- 查找待批改作业和学生提交
- 提取学生答案文本、图片、附件和 PDF/DOCX 文本
- 生成干运行评分计划
- 用户明确确认后提交分数
- 提交后重新拉取页面验证分数是否写入

考试功能当前隐藏/禁用。

## First Run

先克隆仓库并进入目录：

```bash
git clone https://github.com/luoganzhi/chaoxing_teacher_tools.git
cd chaoxing_teacher_tools
```

检查环境：

```bash
python3 chaoxing_portal_tool.py doctor
```

如果提示缺少依赖，运行：

```bash
python3 chaoxing_portal_tool.py setup
```

再检查一次：

```bash
python3 chaoxing_portal_tool.py doctor
```

登录超星：

```bash
python3 chaoxing_portal_tool.py login
```

检查登录状态：

```bash
python3 chaoxing_portal_tool.py doctor --check-login
```

## Python Notes

同一个环境里请始终使用同一个 Python。例如如果你用：

```bash
python3.11 chaoxing_portal_tool.py doctor
```

后续也继续用 `python3.11` 跑 `setup`、`login` 和批改命令。

`setup` 会把依赖安装到本项目的 `.chaoxing_deps/cpythonX.Y/` 目录，不会安装到系统 Python。不同 Python 版本会使用不同的本地依赖目录。

如果 `setup` 报错并显示 pip 自身无法启动，说明当前 Python 安装有问题。换一个可用 Python 后重新跑 `doctor` 和 `setup`。

## Basic Course Flow

列出教师课程：

```bash
python3 chaoxing_portal_tool.py courses
```

查看某门课程的班级：

```bash
python3 chaoxing_portal_tool.py course-classes "课程名称"
```

查看班级任务入口：

```bash
python3 chaoxing_portal_tool.py task-options "课程名称" "班级序号或班级ID"
```

进入作业入口：

```bash
python3 chaoxing_portal_tool.py course-task "课程名称" "班级序号或班级ID" homework
```

## Homework Grading Flow

查看待批改作业：

```bash
python3 chaoxing_portal_tool.py homework-ungraded "课程名称" "班级序号或班级ID"
```

查看某个作业的待批改提交：

```bash
python3 chaoxing_portal_tool.py homework-submissions "课程名称" "班级序号或班级ID" 1
```

提取作业内容给 agent 参考：

```bash
python3 chaoxing_portal_tool.py homework-review-bundle "课程名称" "班级序号或班级ID" 1 --download-assets --max-chars 8000
```

`--download-assets` 会下载学生答案中的图片和附件。生成的 review bundle 会包含：

- 学生答案文本
- 答案图片路径
- 附件文件名和元数据
- PDF/DOCX/TXT 等可提取文本

agent 应该先查看这些内容，再生成评分 JSON。

根据人工/agent 审阅结果生成干运行评分计划：

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed ".chaoxing_review_bundles/review_bundle_...json" "review_scores.json"
```

提交分数前先让用户确认最终名单、分数和理由。确认后再执行：

```bash
python3 chaoxing_portal_tool.py homework-submit-plan ".chaoxing_grade_plans/grade_plan_...json" --commit
```

## Using As An Agent Skill

这个仓库可以作为 agent skill 使用，但不要只复制 `SKILL.md`。完整使用需要这些文件在同一目录：

- `SKILL.md`
- `chaoxing_portal_tool.py`
- `chaoxing_portal_tool.md`
- `chaoxing_browser_check.py`
- `chaoxing_cookie_check.py`
- `requirements.txt`

agent 首次进入新环境时应先运行：

```bash
python3 chaoxing_portal_tool.py doctor
```

缺依赖时运行：

```bash
python3 chaoxing_portal_tool.py setup
```

## Safety

- 不要提交 `.chaoxing_cookies.json`
- 不要提交 `.chaoxing_grade_plans/`
- 不要提交 `.chaoxing_review_bundles/`
- 不要公开学生作业附件、图片和成绩文件
- 不要把账号、密码、cookie 写进聊天记录或代码
- 没有用户明确确认，不要执行带 `--commit` 的提交命令

仓库的 `.gitignore` 已经排除了常见本地运行数据。

## More Commands

完整命令说明见：

- `chaoxing_portal_tool.md`
- `python3 chaoxing_portal_tool.py --help`
