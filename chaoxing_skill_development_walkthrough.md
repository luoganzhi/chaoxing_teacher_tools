# 超星自动化工具与 Skill 开发全过程复盘

这份文档记录本次从“能登录超星”到“能让大模型按教师工作流批改作业并提交分数”，再到“封装成本地 skill”的全过程。目标不是只说明怎么运行，而是让你以后可以自己实现类似工具。

文档不会记录账号、密码、cookie 值或学生隐私内容。

## 最终产物

本次最终形成了两类产物：

1. 自动化脚本

```text
/Users/lgzyy/solo_work/chaoxing_tools/chaoxing_portal_tool.py
```

2. 本地 skill

```text
/Users/lgzyy/.agents/skills/chaoxing-teacher/SKILL.md
```

脚本负责稳定执行具体动作，skill 负责告诉大模型应该如何组织对话、如何调用脚本、什么时候必须等用户确认。

## 核心设计思路

一开始容易把它做成“终端菜单程序”，但这个项目的目标不是让用户在终端里一层层输入数字，而是让大模型成为交互层：

```text
用户：进入超星
模型：列出教学课程
用户：人工智能原理
模型：列出班级，并优先显示用户自己的班级
用户：物联网1班
模型：显示作业界面
用户：第一个作业，所有学生按内容给分
模型：提取学生提交内容，审阅，生成评分计划
用户：提交分数
模型：提交并核对结果
```

因此脚本要做成一组可组合的命令，而不是一个长时间运行的交互式 CLI。大模型每次根据用户意图选择一个命令，拿到结构化结果，再决定下一步。

## 按开发流程复盘：从失败到解决

这一节按真实开发顺序写。每一步都包括：

```text
目标 -> 当时失败/问题 -> 原因判断 -> 解决方案 -> 为什么这么解决
```

后面的章节会再展开 cookie、API、页面解析、附件下载、打分和 skill 封装的具体实现。

### 流程 1：先解决登录，而不是先写业务

目标：

```text
运行脚本时，如果没登录，就提示输入账号和密码；登录成功后保存 cookie，后续直接复用。
```

当时遇到的问题：

```text
一开始尝试弹浏览器界面，但用户反馈“没有弹出登录窗口”或“界面弹了，但没有登录窗口”。
```

原因判断：

1. 浏览器打开门户页时，不一定直接出现登录表单。
2. 有时是已有状态、跳转页、iframe 或学校门户包装页。
3. 浏览器自动化适合人工兜底，但不适合做稳定的基础登录能力。
4. 如果登录都不稳定，后面的课程、作业、提交都没法稳定。

解决方案：

改成 API 登录优先：

```bash
python3 chaoxing_portal_tool.py login
```

脚本做的事：

1. 请求超星登录页。
2. 解析 hidden input。
3. 按登录页要求加密账号密码。
4. 请求 `/fanyalogin`。
5. 登录成功后访问跳转 URL 做 cookie warmup。
6. 保存 `.chaoxing_cookies.json`。

为什么这么解决：

```text
API 登录比浏览器弹窗更稳定，更适合脚本和大模型调用。
浏览器保留为兜底，不作为主链路。
```

### 流程 2：把“终端交互”改成“大模型交互”

目标：

```text
用户说“进入超星”，模型就应该列课程、列班级、问作业，而不是让用户在终端菜单里输入。
```

当时的问题：

```text
一开始容易做成交互式命令行菜单，但用户明确说：不是交互命令，是给大模型当 skill 用。
```

原因判断：

1. 终端菜单要求用户看到终端并输入选项。
2. skill 的使用者是大模型，应该由模型调用一个个确定性命令。
3. 每个命令应该“输入参数 -> 输出结果 -> 退出”，方便模型编排。

解决方案：

把能力拆成多个一次性命令：

```bash
courses
course-classes
task-options
course-task
homework-ungraded
homework-submissions
homework-review-bundle
homework-grade-reviewed
homework-submit-plan
```

为什么这么解决：

```text
大模型擅长根据上下文选择下一步，但不适合被卡在一个长期运行的终端菜单里。
拆成小命令后，模型可以自然地把用户语言映射成命令调用。
```

### 流程 3：课程必须只展示“教的课”

目标：

```text
只展示当前教师教的课程，不展示学生身份下学习的课。
```

当时的问题：

```text
超星页面里“我的课程/学习空间”可能混合展示学习课程和教学课程。
```

原因判断：

1. 用户场景是教师批改作业。
2. 如果把学的课也展示出来，后面班级、作业、批阅接口会错。
3. 需要找教师端课程数据源。

解决方案：

使用教师课程接口：

```text
https://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&rss=1
```

从返回的 `channelList[].content.clazz` 判断课程是否有教师班级。

为什么这么解决：

```text
这个接口直接返回课程和班级结构，比解析学习空间页面更稳定。
只要课程里有 clazz 列表，就能继续走教师端班级/作业流程。
```

### 流程 4：班级要优先显示用户自己的班级

目标：

```text
用户选择课程后，展示班级；优先展示当前用户负责的班级。
```

当时的问题：

```text
同一门课可能有多个教师、多个班级，用户不希望每次从一堆班级里找自己的。
```

原因判断：

1. 班级名里通常包含教师姓名。
2. 当前登录用户姓名可以从 `i.chaoxing.com` 页面里检测。
3. 用用户姓名匹配班级名，可以做一个低成本优先级排序。

解决方案：

1. 访问登录后的空间页。
2. 提取当前用户姓名。
3. 如果班级名包含该姓名，就标记 `[用户]`。
4. 排序时把 `[用户]` 班级放前面。

为什么这么解决：

```text
不需要额外接口，也不改变超星数据，只是在展示层做优先级。
对大模型来说，这能减少选择歧义。
```

### 流程 5：考试功能先做入口，后来屏蔽

目标：

```text
用户希望班级选择后，可以选择进入考试界面或作业界面。
```

当时的问题：

```text
考试入口 URL 可以生成，但浏览器测试时出现登录页、about:blank、上下文 cookie 不稳定等问题。
```

原因判断：

1. 考试页面不只是一个静态 URL。
2. 它可能依赖浏览器登录态、课程入口上下文、前端跳转。
3. 考试是高风险功能，后续可能涉及发布、监考、试卷库等动作。
4. 当前还没有完整定义“考试自动化到底要做什么任务”。

解决方案：

先屏蔽考试：

```python
TASK_ORDER = ("homework",)
```

直接调用考试时返回：

```text
task is currently disabled: exam
```

为什么这么解决：

```text
不稳定功能不应该进入 skill。
作业批改主流程已经可用，考试可以后续单独开发和验证。
```

### 流程 6：找到未批改作业

目标：

```text
用户进入某个班级作业界面后，找出未批改作业。
```

当时的问题：

```text
作业列表不是一个干净的 JSON API，而是 HTML 页面。
```

原因判断：

1. 教师课程入口页里有作业模块 `data-url`。
2. 作业列表 HTML 里能看到作业标题、work_id、待批数量。
3. 只要稳定解析这些 HTML 块，就能实现未批改作业发现。

解决方案：

1. 先访问课程入口。
2. 解析 hidden 字段：`courseid/clazzid/cpi/enc/openc/t`。
3. 解析导航里的作业模块 URL。
4. 请求作业列表。
5. 用正则从 `<li id="work...">` 中提取作业。
6. 用“待批/已交/未交”数字判断未批改。

为什么这么解决：

```text
虽然 HTML 解析比 JSON 脆弱，但这是当前页面里最直接可用的数据。
每个解析结果都有 work_id，可继续进入提交列表。
```

### 流程 7：不能直接随机给分，必须先看提交内容

目标：

```text
给待批学生打分，分数可以总体偏高，但要符合提交内容。
```

当时的问题：

```text
一开始实现了随机/正态分布打分，但用户指出：大模型应该确认提交作业内容是否合适。
```

原因判断：

1. 随机分数不能体现作业质量。
2. 教师批改场景需要基本证据。
3. 低于 70 分尤其需要具体理由。

解决方案：

增加 `homework-review-bundle`：

```bash
python3 chaoxing_portal_tool.py homework-review-bundle "<course>" "<clazz>" "<work>" --download-assets --max-chars 8000
```

让脚本提取每个学生提交内容，再由大模型审阅并生成：

```json
{
  "answer_id": "...",
  "score": 90,
  "content_summary": "...",
  "evidence": "...",
  "reason": "..."
}
```

为什么这么解决：

```text
脚本负责“拿到内容”，大模型负责“理解内容并给出理由”。
这样比纯随机更符合教师批改场景，也便于用户确认。
```

### 流程 8：附件提取第一次失败，原因是混入了题目附件

目标：

```text
下载学生提交的实验报告，而不是下载题目附件。
```

当时的问题：

```text
批阅页里每个学生都显示两个附件，其中一个其实是题目附件 code_and_data.zip。
```

原因判断：

1. 如果直接解析整页 iframe，会把题目附件和学生附件混在一起。
2. 评分时题目附件不应该算学生提交内容。
3. 学生答案一般在 `stuAnswerWords` 区域。

解决方案：

只从学生答案片段里提取附件：

```python
answer_fragments = re.findall(
    r"<dd ... class='stuAnswerWords' ...>(...)</dd>",
    html
)
```

然后生成：

```python
student_answer_attachments
```

为什么这么解决：

```text
题目附件通常在页面其他区域，学生提交附件在答案区域。
按区域解析比按全页附件列表解析更准确。
```

### 流程 9：附件下载遇到 403

目标：

```text
根据 objectid 下载学生提交的 docx/pdf。
```

当时的问题：

```text
/ananas/status/{objectid} 返回 403 或请求失败。
```

原因判断分两层：

1. 沙箱网络限制可能导致请求失败，需要放开网络权限。
2. 即使网络可用，超星附件状态接口也可能检查 Referer/User-Agent。

解决方案：

请求附件状态时增加请求头：

```python
headers = {
    "Referer": MOOC2_BASE_URL + "/",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}
```

同时如果是沙箱网络错误，就用带网络权限的方式重跑。

为什么这么解决：

```text
浏览器真实访问附件时会带 Referer 和 User-Agent。
脚本模拟浏览器必要请求头，可以通过服务端校验。
```

### 流程 10：同名附件覆盖问题

目标：

```text
把每个学生的报告都下载下来。
```

当时的问题：

```text
多个学生的附件名都叫“实验四：机器学习.docx”，下载到同一目录会互相覆盖。
```

原因判断：

```text
文件名不是全局唯一，不能直接用原始 filename 作为本地路径。
```

解决方案：

下载时给文件名前面加学生序号和姓名：

```text
1_学生A_实验四：机器学习.docx
2_学生B_实验四：机器学习.docx
```

为什么这么解决：

```text
保留原始文件名便于识别，同时用学生前缀保证唯一。
```

### 流程 11：docx 抽取失败，原因是图片 CRC 损坏

目标：

```text
从 docx 实验报告里抽取正文，供大模型审阅。
```

当时的问题：

```text
某个 docx 用 python-docx 读取失败，报 Bad CRC-32，原因是文档内某张图片损坏。
```

原因判断：

1. docx 本质是 zip 包。
2. 图片坏了不代表正文 XML 坏了。
3. `python-docx` 会读取文档关系和媒体，可能被坏图片拖垮。

解决方案：

增加 fallback：

```text
直接打开 docx zip -> 读取 word/document.xml -> 提取 w:t 文本节点
```

为什么这么解决：

```text
评分主要需要文字内容，不需要图片本身。
绕过损坏媒体文件，可以最大限度保留可读文本。
```

### 流程 12：提交分数前必须生成计划

目标：

```text
模型给出最终分数，但不能立刻提交。
```

当时的问题：

```text
真实成绩写入是高风险动作。如果模型生成分数后马上提交，用户没有确认机会。
```

原因判断：

1. 分数属于真实业务数据。
2. 用户需要看到所有学生最终分数和理由。
3. 提交应该是显式动作。

解决方案：

先生成 dry-run plan：

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed review_bundle.json review_scores.json
```

保存到：

```text
.chaoxing_grade_plans/grade_plan_...json
```

展示摘要后，等待用户说：

```text
提交分数
```

为什么这么解决：

```text
plan 文件把“模型建议”和“真实提交”隔离开。
用户确认后，提交的是同一份 plan，不会临时重新生成分数。
```

### 流程 13：提交成功后还要核对

目标：

```text
提交分数后确认页面实际分数和计划一致。
```

当时的问题：

```text
接口返回“操作成功”只能说明请求成功，不代表页面最终状态一定正确。
```

原因判断：

可能存在：

1. 某个 answer_id 提交失败。
2. 页面分数没有刷新。
3. 接口返回成功但部分数据不一致。
4. 提交计划和实际页面不一致。

解决方案：

提交后重新获取提交列表：

```text
GET /mooc2-ans/work/mark-list?status=0
```

按 `answer_id` 比对：

```text
expected
matched
mismatch
missing
```

为什么这么解决：

```text
最终可信结果应该来自系统当前页面/接口状态，而不是提交请求的瞬时返回。
```

### 流程 14：不要过早写 skill

目标：

```text
把完整超星流程封装成 skill。
```

当时的问题：

```text
我曾经过早生成 skill，用户指出流程还不完善，要求先不要做成 skill。
```

原因判断：

1. skill 是给以后复用的流程规范。
2. 如果把半成品写进 skill，会固化错误流程。
3. 当时作业审阅、附件下载、提交核对都还没稳定。

解决方案：

先继续开发脚本，完成真实测试：

```text
登录 -> 课程 -> 班级 -> 作业 -> 提交内容 -> 内容审阅 -> 评分计划 -> 提交 -> 核对
```

等用户说“现在写成 skill”后，再创建：

```text
/Users/lgzyy/.agents/skills/chaoxing-teacher/SKILL.md
```

为什么这么解决：

```text
脚本负责确定性动作，skill 负责稳定流程。流程不稳定时，不应该写 skill。
```

### 流程 15：最终 skill 写了什么

最终 skill 固化的是工作流，而不是复制代码。

它告诉大模型：

1. 什么时候触发。
2. 调用哪个本地脚本。
3. 课程、班级、作业怎么一步步选。
4. 考试当前禁用。
5. 作业评分必须先提取内容。
6. 低于 70 分必须写理由。
7. 提交前必须展示计划并等确认。
8. 提交后必须核对。
9. 不要泄露账号、密码、cookie。

为什么这么解决：

```text
skill 最适合保存“流程和边界”，不适合替代底层脚本。
底层 API 变化时，只改脚本；交互策略变化时，再改 skill。
```

## 文件结构

当前项目主要文件：

```text
chaoxing_portal_tool.py
chaoxing_portal_tool.md
chaoxing_skill_development_walkthrough.md
.chaoxing_cookies.json
.chaoxing_grade_plans/
.chaoxing_review_bundles/
.skill_build/chaoxing-teacher/
```

各文件职责：

- `chaoxing_portal_tool.py`：主工具，负责登录、课程、班级、作业、评分计划、提交和核对。
- `chaoxing_portal_tool.md`：工具命令说明。
- `chaoxing_skill_development_walkthrough.md`：本复盘文档。
- `.chaoxing_cookies.json`：保存登录 cookie，不要提交到公开仓库。
- `.chaoxing_grade_plans/`：保存 dry-run 评分计划，提交时按这个文件执行。
- `.chaoxing_review_bundles/`：保存学生提交内容、附件下载路径、抽取文本。
- `.skill_build/chaoxing-teacher/`：skill 草稿，后来复制到本地 skill 目录。

## 第一步：登录与 Cookie

最开始用户希望“运行脚本时，如果没登录，就提示输入账号和密码”。所以我们没有只做浏览器弹窗登录，而是优先用 API 风格登录：

```bash
python3 chaoxing_portal_tool.py login
```

脚本提示账号、密码，调用超星登录接口，保存 cookies 到：

```text
.chaoxing_cookies.json
```

后续命令都复用这个 cookie 文件。

登录相关命令：

```bash
python3 chaoxing_portal_tool.py api-status
python3 chaoxing_portal_tool.py login
python3 chaoxing_portal_tool.py clear
```

实现重点：

- 不在代码里写死账号密码。
- 不在聊天或日志里输出密码、cookie 值。
- cookie 文件权限设置为仅当前用户可读写。
- 如果 cookie 失效，自动提示重新登录。

## Cookie 获取和使用详解

这一部分是整个工具的基础。只要 cookie 处理正确，后续课程、班级、作业、提交分数都可以走 HTTP 请求，不需要每次打开浏览器登录。

### 1. 为什么要保存 cookie

超星登录成功后，服务端会在响应里下发多个 cookie。之后访问课程、作业、批阅接口时，请求只要带上这些 cookie，服务端就认为这是已登录用户。

所以自动化工具的核心是：

```text
账号密码登录一次 -> 保存 cookie -> 后续所有命令复用 cookie
```

这比每次弹浏览器扫码/输入密码稳定，也更适合大模型调用脚本。

### 2. Cookie 文件格式

脚本把 cookie 保存成 JSON：

```json
{
  "created_at": "2026-05-28T22:17:00+0800",
  "cookies": [
    {
      "name": "cookie_name",
      "value": "cookie_value",
      "domain": ".chaoxing.com",
      "path": "/",
      "secure": false,
      "expires": 1780600640,
      "httpOnly": true
    }
  ]
}
```

字段含义：

- `name`：cookie 名称。
- `value`：cookie 值，敏感，不要打印。
- `domain`：cookie 生效域名，例如 `.chaoxing.com`、`passport2.chaoxing.com`。
- `path`：cookie 生效路径，通常是 `/`。
- `secure`：是否只允许 HTTPS。
- `expires`：过期时间，Unix 时间戳；没有则是会话 cookie。
- `httpOnly`：浏览器 JavaScript 不能读取，但自动化工具仍可注入。

保存时设置文件权限：

```python
os.chmod(path, 0o600)
```

这样只有当前系统用户能读写。

### 3. API 登录的完整流程

登录命令：

```bash
python3 chaoxing_portal_tool.py login
```

内部流程如下。

第一步，准备一个 `requests.Session()`：

```python
session = requests.Session()
session.headers.update(request_headers())
```

`Session` 很重要，因为它会自动保存服务端返回的 cookie。

第二步，请求登录页：

```text
https://passport2.chaoxing.com/login?newversion=true&fid=1971&refer=...
```

登录页里有一些 hidden input，例如：

```text
fid
refer
t
forbidotherlogin
validate
doubleFactorLogin
independentId
independentNameId
```

这些值要带回登录请求。不要自己硬编码，应该从页面里解析。

第三步，根据登录页的 `t` 字段决定是否加密账号密码。

本项目里，如果 `t == "true"`，会用 AES-CBC + PKCS7 后 base64：

```python
post_username = aes_encrypt_base64(username)
post_password = aes_encrypt_base64(password)
```

密钥是代码里的：

```python
TRANSFER_KEY = "u2oh6Vu^HWe4_AES"
```

第四步，提交登录请求：

```text
POST https://passport2.chaoxing.com/fanyalogin
```

请求数据大致是：

```python
payload = {
    "fid": hidden.get("fid", args.fid),
    "uname": post_username,
    "password": post_password,
    "refer": hidden.get("refer", refer),
    "t": t_value,
    "forbidotherlogin": hidden.get("forbidotherlogin", "0"),
    "validate": hidden.get("validate", ""),
    "doubleFactorLogin": hidden.get("doubleFactorLogin", "0"),
    "independentId": hidden.get("independentId", ""),
    "independentNameId": hidden.get("independentNameId", ""),
}
```

请求头里要模拟 AJAX 登录：

```python
headers = {
    "Origin": "https://passport2.chaoxing.com",
    "Referer": login_page,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}
```

第五步，检查登录结果。

登录接口返回 JSON。常见情况：

- `status == true`：登录成功。
- `containTwoFactorLogin == true`：需要二次验证。
- `status == false`：账号密码错误、验证码、风控或其他失败。

如果需要二次验证，脚本不要伪造绕过，而是直接报错或走浏览器兜底。

第六步，登录后 warmup。

登录成功后，接口会返回一个跳转 URL。脚本会继续访问：

```python
session.get(target_url, allow_redirects=True)
session.get(args.url, allow_redirects=True)
```

这一步很重要。很多站点不是登录接口一次响应就下发所有 cookie，而是在后续跳转过程中继续设置 cookie。warmup 后 cookie 更完整。

第七步，保存 cookie。

```python
save_cookie_file(session, args.cookie_file)
```

保存的是 `session.cookies` 里当前所有 cookie，而不是只保存某一个 token。

### 4. 用 cookie 发 HTTP 请求

后续所有 API 命令都通过：

```python
request_session_from_cookie_file(path)
```

重新构造一个 `requests.Session()`：

```python
session = requests.Session()
session.headers.update(request_headers())
for cookie in load_cookie_file(path):
    session.cookies.set(
        name,
        value,
        domain=domain,
        path=path_value,
    )
```

这样后续请求：

```python
session.get(...)
session.post(...)
```

都会自动带上 cookie。

这就是为什么 `courses`、`homework-ungraded`、`homework-submit-plan` 不需要再次输入密码。

### 5. 判断 cookie 是否还有效

不能只判断文件是否存在。cookie 文件存在，但可能已经过期或被服务端踢下线。

所以脚本提供：

```bash
python3 chaoxing_portal_tool.py api-status
```

内部会用保存的 cookie 访问：

```text
https://i.chaoxing.com/
```

然后检查：

- 最终 URL 是否跳到登录页。
- 页面标题/正文是否包含登录提示。
- 页面是否包含“学习空间”“我的课程”等登录后特征。

核心判断函数是：

```python
looks_logged_out(url, title, body)
```

如果判断已登出，就重新调用登录流程。

### 6. 浏览器里使用 cookie

HTTP 请求和浏览器是两套环境。`requests.Session()` 里的 cookie 不会自动进入 Chrome。

如果要用浏览器打开页面，需要把 cookie 注入 `agent-browser`：

```python
inject_cookie_file_into_browser(browser_args, cookie_file)
```

每个 cookie 会调用：

```bash
agent-browser cookies set <name> <value> \
  --url https://chaoxing.com/ \
  --domain .chaoxing.com \
  --path /
```

这里踩过一个坑：只传 `--domain` 和 `--path` 不够稳定，浏览器里可能看不到 cookie。后来改成同时传 `--url`：

```python
cookie_url = "https://" + domain.lstrip(".") + path_value
```

然后再传：

```python
--url cookie_url
--domain domain
--path path_value
```

如果原 cookie 有这些属性，也要一起带上：

```python
--secure
--httpOnly
--expires <timestamp>
```

注意：`httpOnly` 的 cookie 不能被网页 JavaScript 读取，但浏览器请求仍然会自动携带，所以注入时要保留。

### 7. 验证浏览器 cookie 是否成功

不要直接打印 cookie 值。可以只查看名称和域名：

```bash
agent-browser --session scujcc-chaoxing-portal cookies --json \
  | jq -r '.data.cookies[]? | [.name,.domain,.path] | @tsv'
```

验证是否登录：

```bash
agent-browser --session scujcc-chaoxing-portal open https://i.chaoxing.com/
agent-browser --session scujcc-chaoxing-portal get title
agent-browser --session scujcc-chaoxing-portal get url
```

如果打开后标题是“个人空间”，说明浏览器登录态可用。如果跳到：

```text
passport2.chaoxing.com/login
```

说明 cookie 没有成功注入、cookie 失效，或当前页面需要额外上下文。

### 8. 为什么有时 API 可用但浏览器不可用

本次测试时出现过：

```text
API 请求能拿课程和作业，但浏览器打开考试页跳登录。
```

原因是：

1. `requests.Session()` 和 Chrome 是不同 cookie jar。
2. Chrome 没有注入 cookie 时，打开页面肯定跳登录。
3. 有些超星页面需要先访问 `i.chaoxing.com` 或课程入口，让浏览器建立上下文 cookie。

所以浏览器打开页面时推荐顺序是：

```text
注入 cookie
打开 https://i.chaoxing.com/
打开课程入口 course_entry_url
打开目标模块 URL
```

不过当前考试功能已屏蔽，作业主流程主要走 HTTP API，不依赖浏览器。

### 9. Cookie 失效时的处理策略

命令默认会先检查 cookie：

```python
ensure_api_logged_in(args)
```

如果 cookie 可用，直接继续。

如果 cookie 不可用：

```text
saved login unavailable: ...
```

然后提示用户输入账号密码，重新登录并覆盖 cookie 文件。

某些命令会用：

```bash
--no-auto-login
```

这表示不要自动提示账号密码。适合我们已经知道 cookie 有效、只想避免命令突然卡在输入密码的场景。

### 10. Cookie 安全原则

实现类似工具时要遵守这些规则：

1. 不要把 cookie 写进代码。
2. 不要把 cookie 打印到聊天窗口。
3. 不要把 `.chaoxing_cookies.json` 提交到公开仓库。
4. 保存 cookie 文件时设置 `0o600` 权限。
5. 调试 cookie 时只打印 `name/domain/path`，不要打印 `value`。
6. 登录失败、二次验证、验证码时不要尝试绕过，应该转为人工处理或浏览器兜底。
7. 如果用户要求清除登录态，删除 cookie 文件或运行：

```bash
python3 chaoxing_portal_tool.py clear
```

## 如何从零发现 API

这一节讲“怎么知道应该请求哪个 URL”。这是开发自动化工具最核心的能力。

### 1. 先用真实浏览器走一遍人工流程

不要一开始就写代码。先像普通用户一样操作一遍：

```text
打开超星 -> 登录 -> 我的课程 -> 进入课程 -> 选择班级 -> 进入作业 -> 点击批阅 -> 打分
```

一边操作，一边打开浏览器开发者工具：

```text
Chrome DevTools -> Network
```

建议设置：

```text
Preserve log: 打开
Disable cache: 打开
过滤器: Fetch/XHR、Doc、All 来回切
```

为什么要 `Preserve log`：很多页面会跳转，如果不保留日志，关键请求会被刷新掉。

### 2. 找 API 的基本方法

每完成一个页面动作，就看 Network 里新增了哪些请求。

常见判断方法：

1. 看请求 URL 名称

例如看到：

```text
backclazzdata
work/list
mark-list
review-work
markscore
```

基本能猜到含义。

2. 看请求类型

```text
document/html：页面主体，通常需要解析 HTML。
fetch/xhr/json：接口数据，优先用。
script/image/css：通常不是业务接口。
```

3. 看响应内容

点开请求的 `Response`：

- 如果是 JSON，优先用 JSON。
- 如果是 HTML，找里面的表格、列表、隐藏 input、data-url。
- 如果是跳登录页，说明 cookie 没带上或权限不对。

4. 看 Query String Parameters 和 Form Data

重点记录：

```text
courseid
clazzid
workid
cpi
enc
openc
t
pages
status
answerIds
score
```

这些参数一般就是你脚本要构造的参数。

### 3. 把浏览器请求复制成 curl

在 DevTools 的 Network 里：

```text
右键某个请求 -> Copy -> Copy as cURL
```

然后在终端里运行这个 curl。能跑通，说明你已经捕获了完整请求。

接下来逐步删掉不必要的 header，保留最小集合：

```text
Cookie
User-Agent
Referer
Origin
X-Requested-With
Content-Type
```

一般规则：

- GET 页面：`Cookie + User-Agent` 通常够。
- AJAX 登录：需要 `Origin + Referer + X-Requested-With`。
- 附件状态/下载：可能需要 `Referer + User-Agent`。
- POST 写操作：要保留表单参数，必要时保留 `Content-Type`。

### 4. 从 curl 转成 requests

curl 能跑通后，再转成 Python：

```python
session = requests.Session()
session.headers.update(request_headers())

response = session.get(url, params=params, timeout=20)
response.raise_for_status()
```

POST：

```python
response = session.post(url, data=payload, timeout=20)
response.raise_for_status()
```

如果接口返回 JSON：

```python
data = response.json()
```

如果返回 HTML：

```python
html = response.text
```

然后进入解析流程。

### 5. 判断一个请求是不是“真正 API”

不是所有请求都值得写进脚本。

优先级：

1. JSON API
   - 最稳定。
   - 字段清晰。
   - 最适合脚本。

2. 局部 HTML API
   - 比完整页面好。
   - 可以用 regex/HTML parser 提取列表。

3. 完整页面 HTML
   - 可用，但容易受页面改版影响。
   - 需要多做校验。

4. 浏览器点击
   - 最不稳定。
   - 只作为兜底或人工确认。

本项目里，课程列表是 JSON API；作业列表、提交列表、批阅页主要是 HTML，需要解析。

### 6. 本项目里发现到的关键接口

登录页：

```text
GET https://passport2.chaoxing.com/login
```

登录接口：

```text
POST https://passport2.chaoxing.com/fanyalogin
```

登录状态检查：

```text
GET https://i.chaoxing.com/
```

教师课程列表：

```text
GET https://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&rss=1
```

课程入口：

```text
GET https://mooc1.chaoxing.com/course/isNewCourse
```

教师课程页最终会跳到类似：

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/tch?... 
```

作业列表：

```text
GET https://mooc2-ans.chaoxing.com/mooc2-ans/work/list
```

作业基础信息：

```text
GET https://mooc2-ans.chaoxing.com/mooc2-ans/work/workinfo
```

待批/已批提交列表：

```text
GET https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark-list
```

单个学生批阅页：

```text
GET https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work
```

附件状态：

```text
GET https://mooc2-ans.chaoxing.com/ananas/status/{objectid}
```

提交分数：

```text
POST https://mooc2-ans.chaoxing.com/mooc2-ans/work/markscore
```

### 7. 参数从哪里来

很多参数不是你凭空知道的，而是从上一步页面里解析出来的。

课程列表接口返回：

```text
course_id
clazz_id
cpi
clazz_name
teacher
term
```

课程入口页隐藏字段返回：

```text
courseid
clazzid
cpi
enc
openc
t
```

作业列表页返回：

```text
work_id
作业标题
待批数量
已交数量
未交数量
mark_url
```

提交列表页返回：

```text
answer_id
student_name
student_no
submitted_at
score
review_url
```

批阅页返回：

```text
full_score
student answer text
student answer attachments
attachment objectid
```

打分接口需要：

```text
courseid
clazzid
cpi
workid
answerIds
score
markScore
markAnswerIds
markType
```

这就是自动化工具的链式数据流：

```text
课程接口 -> course_id / cpi
班级列表 -> clazz_id
课程入口 -> enc / openc / t
作业列表 -> work_id
提交列表 -> answer_id / review_url
批阅页 -> 学生内容 / 附件
评分计划 -> answer_id + score
提交接口 -> 写入分数
提交列表 -> 核对分数
```

## 如何获取页面内容

“获取界面内容”有两种路线：

1. HTTP 请求获取 HTML/JSON。
2. 浏览器自动化读取页面。

优先用 HTTP 请求，因为稳定、快、容易测试。只有页面强依赖前端渲染、验证码、复杂交互时才用浏览器。

### 1. 用 HTTP 获取 HTML

示例：获取课程入口页。

```python
session = request_session_from_cookie_file(cookie_file)
response = session.get(entry_url, timeout=20, allow_redirects=True)
response.raise_for_status()
html = response.text
```

拿到 HTML 后，先做三件事：

1. 判断是不是登录页。
2. 抽取隐藏 input。
3. 抽取你要的列表/链接/按钮数据。

判断登录页：

```python
title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
title = ...
if looks_logged_out(response.url, title, html):
    raise ToolError("saved cookies are logged out")
```

### 2. 解析 hidden input

很多网页把关键参数放在隐藏 input：

```html
<input type="hidden" name="courseid" value="204565237">
<input type="hidden" name="clazzid" value="140622283">
<input type="hidden" name="enc" value="...">
```

脚本统一用：

```python
parse_hidden_inputs(html)
```

实现思路：

```python
for input_tag in re.finditer(r"<input\b[^>]*>", html):
    attrs = html_attrs(input_tag)
    if attrs.get("type") == "hidden":
        key = attrs.get("name") or attrs.get("id")
        value = attrs.get("value", "")
```

这样课程入口、批阅页、分页信息都可以复用。

### 3. 解析 HTML 属性

页面里经常有：

```html
<a data-url="/mooc2-ans/work/list" title="作业">
<ul id="55478986" createid="...">
<iframe class="attach-iframe" filename="实验报告.docx" objectid="...">
```

所以写了：

```python
html_attrs(tag)
```

它从一个 HTML tag 字符串里提取属性：

```python
{
  "data-url": "/mooc2-ans/work/list",
  "title": "作业"
}
```

这比手写很多 `split('"')` 稳定。

### 4. 解析课程导航

课程入口页里有左侧导航，每个导航项类似：

```html
<li dataname="zy" pageheader="6">
  <a title="作业" data-url="/mooc2-ans/work/list">
</li>
```

脚本解析出：

```python
{
  "zy": {
    "module": "zy",
    "title": "作业",
    "data_url": "/mooc2-ans/work/list",
    "page_header": "6"
  }
}
```

然后构造作业 URL：

```text
base_url + ?courseid=...&clazzid=...&cpi=...&enc=...&openc=...&t=...
```

关键点：不要写死完整 URL，只写死模块的 fallback 路径，优先从页面 `data-url` 读取。

### 5. 解析纯文本

HTML 里有很多标签、空格、换行。脚本用：

```python
compact_text(fragment)
```

做这些处理：

1. 去掉 script/style。
2. 把 `<br>` 转成换行。
3. 去掉 HTML 标签。
4. HTML entity 反转义。
5. 合并多余空白。

这样可以把复杂 HTML 变成适合匹配的文本。

例如作业列表里可能显示：

```text
实验4：机器学习 11 待批 28 已交 0 未交
```

然后用正则提取：

```python
counts = re.search(r"(\d+)\s*待批\s*(\d+)\s*已交\s*(\d+)\s*未交", plain)
```

### 6. 获取作业列表

作业列表不是 JSON，而是 HTML。

请求参数：

```python
{
    "pages": page,
    "pageSize": "12",
    "status": "-1",
}
```

页面中每个作业块大致是：

```html
<li id="work53018076">
  ...
  <a href="/mooc2-ans/work/mark?id=53018076...">批阅</a>
  ...
</li>
```

解析方法：

```python
for block in re.finditer(r"<li\b[^>]*id=['\"]work\d+['\"][\s\S]*?</li>", html):
    work_id = query_value(mark_url, "id") or attrs["id"].removeprefix("work")
    title = ...
    pending/submitted/unsubmitted = ...
```

这个过程得到：

```json
{
  "work_id": "53018076",
  "title": "实验4：机器学习",
  "pending_count": 11,
  "submitted_count": 28,
  "unsubmitted_count": 0
}
```

### 7. 获取提交列表

提交列表接口：

```text
GET /mooc2-ans/work/mark-list
```

核心参数：

```python
{
    "courseid": course_id,
    "clazzid": clazz_id,
    "workid": work_id,
    "submit": "true",
    "status": "3",
    "cpi": cpi,
    "pages": page,
    "size": 100,
}
```

`status` 的含义：

```text
3：待批
4：已批
0：全部/用于核对
```

页面中每个学生提交行类似：

```html
<ul class="dataBody_td" id="55478986" createid="...">
  <div class="py_name">学生姓名</div>
  <input class="scoreInput" value="90">
  <a data="/mooc2-ans/work/library/review-work?...">
</ul>
```

解析得到：

```json
{
  "answer_id": "55478986",
  "student_name": "...",
  "student_no": "...",
  "submitted_at": "...",
  "score": "",
  "review_url": "https://mooc2-ans.chaoxing.com/..."
}
```

这里的 `review_url` 是后面获取学生具体提交内容的入口。

### 8. 获取单个批阅页内容

批阅页：

```text
GET /mooc2-ans/work/library/review-work?...
```

拿到 HTML 后，主要找：

```html
<dd class="stuAnswerWords">
  学生答案文本
  <iframe class="attach-iframe" filename="..." objectid="...">
</dd>
```

脚本只从 `stuAnswerWords` 里提取学生附件，避免把题目附件混进去。

核心字段：

```python
student_answers
answer_images
student_answer_attachments
full_score
text_excerpt
```

### 9. 获取附件内容

批阅页里附件 iframe 只给：

```text
filename
filetype
objectid
```

不能直接当下载链接。真实流程：

```text
objectid -> /ananas/status/{objectid} -> download URL -> 下载文件
```

代码流程：

```python
status_response = session.get(
    MOOC2_BASE_URL + "/ananas/status/" + objectid,
    headers=headers,
)
status = status_response.json()
download_url = status["download"]
```

然后下载：

```python
response = session.get(download_url, headers=headers)
```

下载后按文件类型抽取文本：

```text
docx -> python-docx，失败时读 word/document.xml
pdf -> pdfplumber
txt/py/csv/md -> 直接读文本
zip -> 列出文件名
```

最终放进 bundle：

```json
"downloaded_assets": [
  {
    "filename": "学生报告.docx",
    "objectid": "...",
    "path": ".chaoxing_review_bundles/assets_.../...",
    "extracted_text": "报告正文..."
  }
]
```

### 10. 用浏览器获取界面内容

有些时候 API/HTML 解析不够，或者需要确认真实页面。可以用 `agent-browser`。

打开页面：

```bash
agent-browser --session scujcc-chaoxing-portal open "https://..."
```

获取标题和 URL：

```bash
agent-browser --session scujcc-chaoxing-portal get title
agent-browser --session scujcc-chaoxing-portal get url
```

获取可交互元素：

```bash
agent-browser --session scujcc-chaoxing-portal snapshot -i -c -d 4
```

示例输出：

```text
- textbox "试卷名" [ref=e1]
- link "新建考试" [ref=e3]
- generic "全部" clickable
```

这适合确认页面是否加载成功，但不适合批量数据提取。批量数据还是优先 HTTP API。

### 11. 如何判断页面内容是否可信

拿到页面后，不要直接相信它是目标页面。至少检查：

1. URL 是否还在目标域名。
2. 是否跳到了 `passport2.chaoxing.com/login`。
3. title 是否是预期页面。
4. 页面中是否有预期关键词。
5. 关键隐藏字段是否存在。
6. 列表数量是否和页面显示一致。

例如课程入口页必须有：

```text
courseid
clazzid
cpi
enc
openc
t
```

缺任何一个，都不要继续构造作业 URL。

### 12. 调试接口时的最小步骤

以后遇到新页面，可以按这个顺序：

1. 浏览器手动操作一次。
2. DevTools Network 找请求。
3. Copy as cURL。
4. 终端运行 curl。
5. 删除多余 header，保留必要 header。
6. 用保存的 cookie 重放请求。
7. 判断返回是 JSON 还是 HTML。
8. JSON 就按字段解析。
9. HTML 就先找 hidden input、列表块、链接、iframe。
10. 写一个最小 Python 函数请求页面。
11. 写一个 parse 函数只负责解析。
12. 加校验：登录页、缺字段、空列表、多匹配。
13. 封装成命令。
14. 先 dry-run。
15. 涉及写操作时，必须二次确认和结果核对。

## 第二步：只展示“教的课”

用户明确要求“主要展示教的课，学的课不展示”。所以课程列表来自教师端课程数据，而不是学习空间里的全部课程。

命令：

```bash
python3 chaoxing_portal_tool.py courses
```

它输出教学课程，例如：

```text
1. 人工智能原理 ...
```

大模型拿到这个列表后，不应该让用户输入课程 ID，而是直接用自然语言匹配：

```text
用户：人工智能
```

脚本支持课程名、部分课程名或 course_id。

## 第三步：班级选择，并优先用户自己的班级

用户选中课程后，调用：

```bash
python3 chaoxing_portal_tool.py course-classes 人工智能原理
```

脚本会检测当前登录用户名称，并把班级名里包含该用户姓名的班级标为：

```text
[用户]
```

这样模型展示班级时，应该优先把 `[用户]` 班级放在用户容易看到的位置。

这一步的关键不是“列出所有班级”本身，而是让大模型能够理解：

```text
用户说“物联网1班”时，应该匹配到当前课程下对应班级。
用户说“刚刚的班级”时，应该复用上下文里的班级。
```

## 第四步：任务入口，考试先屏蔽

一开始我们做了“作业界面”和“考试界面”两个入口：

```bash
python3 chaoxing_portal_tool.py task-options 人工智能原理 140622283
```

后来测试考试入口时发现，考试页面涉及浏览器登录态、课程入口上下文和考试模块加载顺序，还没有形成稳定的完整工作流。用户决定“后面再开发，先把考试屏蔽”。

因此当前只展示：

```text
1. 作业界面
```

直接调用考试会返回：

```text
task is currently disabled: exam
```

实现方式：

```python
TASK_ORDER = ("homework",)
```

`TASK_DEFINITIONS` 里可以保留 exam 的定义，方便以后恢复，但 `TASK_ORDER` 不包含 exam 时，大模型和用户都看不到考试入口。

## 第五步：找未批改作业

进入作业流程后，先找待批作业：

```bash
python3 chaoxing_portal_tool.py homework-ungraded 人工智能原理 140622283
```

输出包括：

```text
homeworks:
  1. 实验4：机器学习 (work_id=..., pending=11, submitted=28, unsubmitted=0)
```

当用户说“第一个”时，大模型要把它解析为这个列表里的第一个未批改作业。

然后查看待批学生：

```bash
python3 chaoxing_portal_tool.py homework-submissions 人工智能原理 140622283 1
```

这一步只查看，不打分、不提交。

## 第六步：提取学生提交内容

用户希望“更准确的打分”，不能只随机给分。因此我们增加了审阅 bundle：

```bash
python3 chaoxing_portal_tool.py homework-review-bundle 人工智能原理 140622283 1 --download-assets --max-chars 8000 --no-auto-login
```

这个命令做几件事：

1. 打开每个待批学生的批阅页。
2. 提取学生答案区域。
3. 区分“题目附件”和“学生提交附件”。
4. 下载学生提交附件。
5. 从附件中抽取文本。
6. 保存为 JSON bundle。

输出示例：

```text
bundle_file: .chaoxing_review_bundles/review_bundle_...json
asset_dir: .chaoxing_review_bundles/assets_...
reviews: 11
```

### 附件下载的坑

超星附件 iframe 里有 `objectid`，不能直接靠 iframe 内容拿文件。需要访问：

```text
https://mooc2-ans.chaoxing.com/ananas/status/{objectid}
```

返回 JSON 里有真实下载地址。

这里遇到过 403。解决方法是加浏览器式请求头：

```python
headers = {
    "Referer": MOOC2_BASE_URL + "/",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}
```

### 题目附件和学生附件要分开

批阅页里可能同时出现：

- 题目附件，例如代码包、数据集。
- 学生提交附件，例如实验报告 docx/pdf。

如果不区分，就会把题目附件也当作学生答案。最终实现时，只从学生答案区域 `stuAnswerWords` 内提取附件，生成：

```json
"student_answer_attachments": [...]
```

### 同名附件不能覆盖

多个学生可能都上传：

```text
实验四：机器学习.docx
```

所以下载时文件名加了学生前缀：

```text
序号_学生名_原文件名
```

### 文档抽取

支持：

- `.docx`
- `.pdf`
- `.txt`
- `.py`
- `.csv`
- `.md`
- `.zip` 文件列表

`.docx` 遇到图片 CRC 损坏时，`python-docx` 可能失败。后来补了 fallback：直接读取 docx 里的 `word/document.xml`，绕过坏图片。

## 第七步：让大模型按内容打分

有了 bundle 后，大模型不能直接随机给分，而要读取：

```json
reviews[].downloaded_assets[].extracted_text
```

并判断：

- 是否是本次作业主题。
- 是否有完整实验流程。
- 是否有代码/模型/数据/指标/分析。
- 是否有明显跑题。
- 是否空白或附件无效。

用户的偏好是：

```text
尽量 70 分以上。
如果低于 70，必须给充分理由。
```

因此我们设计了评分 JSON：

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

然后生成 dry-run 评分计划：

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed review_bundle.json review_scores.json
```

这个命令会校验：

- 每个待批学生是否都有分数。
- 分数是否在满分范围内。
- 是否都有 reason。
- 低于 70 是否有足够具体的理由。

它只生成计划，不提交。

## 第八步：评分计划和提交确认

评分计划保存在：

```text
.chaoxing_grade_plans/grade_plan_...json
```

模型必须把最终摘要展示给用户，例如：

```text
1. 学生A -> 90 | reason: ...
2. 学生B -> 87 | reason: ...
3. 学生C -> 62 | reason: 与本次实验主题不匹配 ...
```

然后停止，等用户明确说：

```text
提交分数
```

才执行：

```bash
python3 chaoxing_portal_tool.py homework-submit-plan .chaoxing_grade_plans/grade_plan_...json --commit --no-auto-login
```

这个设计很重要：大模型可以建议分数，但不能自动提交真实成绩。

## 第九步：提交后核对

提交成功不代表页面上的分数一定正确。用户要求“提交完了要确认提交的分数是否正确”，所以 `homework-submit-plan --commit` 后会重新拉取批阅列表并比对：

```text
verification: expected=11, matched=11, mismatch=0, missing=0
```

如果出现 mismatch 或 missing，要立即告诉用户哪些学生不一致。

实现思路：

1. 按 plan 调用超星打分接口。
2. 重新获取该作业的提交列表。
3. 按 `answer_id` 对比计划分数和页面实际分数。
4. 输出 expected/matched/mismatch/missing。

## 第十步：随机/正态分布作为 fallback

用户曾希望“70-95，用正态分布生成分数”。这个功能保留为 fallback：

```bash
python3 chaoxing_portal_tool.py homework-grade-random 人工智能原理 140622283 1 --score-range 70-95 --distribution normal
```

但后面用户又明确要求“至少要大模型确认提交内容是否合适”，所以现在的原则是：

```text
有内容可读时，优先内容审阅评分。
随机/正态分布只适合用户明确要求不看内容，或内容不可用时。
```

## 第十一步：封装成本地 Skill

脚本稳定后，才把流程写成 skill。

skill 安装位置：

```text
/Users/lgzyy/.agents/skills/chaoxing-teacher/SKILL.md
```

skill 的作用不是替代脚本，而是告诉大模型：

- 什么时候触发。
- 应该按什么顺序调用脚本。
- 怎么保留上下文。
- 什么情况下必须停下来等用户确认。
- 考试功能当前禁用。
- 低于 70 分必须有理由。

skill frontmatter 里最重要的是 `description`，因为这是触发依据。它要写得具体，比如包含：

```text
进入超星、查课程、进入班级、作业界面、批改作业、未批改作业、给分、提交分数
```

skill 里还写了安全边界：

- 不输出 cookie。
- 不输出密码。
- 不自动提交成绩。
- 不重评已提交作业，除非用户明确要求。
- 考试隐藏，直到继续开发。

## 为什么不是一开始就写 Skill

中间用户提醒过：

```text
现在 skill 并不完善，为什么你就直接生成了 skill？
先不要把这个做成 skill，我做完了会让你做成 skill。
```

这是一个关键经验：skill 应该封装稳定流程，而不是封装半成品。

合理顺序应该是：

1. 先把脚本能力做出来。
2. 用真实流程测试。
3. 修掉接口、解析、下载、提交、核对这些坑。
4. 用户确认流程满意。
5. 再写 skill。

## 关键命令清单

登录：

```bash
python3 chaoxing_portal_tool.py api-status
python3 chaoxing_portal_tool.py login
```

课程与班级：

```bash
python3 chaoxing_portal_tool.py courses
python3 chaoxing_portal_tool.py course-classes "人工智能原理"
python3 chaoxing_portal_tool.py task-options "人工智能原理" "140622283"
```

作业：

```bash
python3 chaoxing_portal_tool.py homework-ungraded "人工智能原理" "140622283"
python3 chaoxing_portal_tool.py homework-submissions "人工智能原理" "140622283" "1"
python3 chaoxing_portal_tool.py homework-review-bundle "人工智能原理" "140622283" "1" --download-assets --max-chars 8000 --no-auto-login
```

内容审阅评分：

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed review_bundle.json review_scores.json
```

随机 fallback：

```bash
python3 chaoxing_portal_tool.py homework-grade-random "人工智能原理" "140622283" "1" --score-range 70-95 --distribution normal
```

提交并核对：

```bash
python3 chaoxing_portal_tool.py homework-submit-plan grade_plan.json --commit --no-auto-login
```

## 自己实现类似工具的通用方法

以后你要做别的平台，可以按这个顺序：

1. 先跑通登录
   - 优先 API 登录。
   - 保存 cookie。
   - 做一个 status/check 命令。

2. 把页面动作拆成小命令
   - list courses
   - list classes
   - list tasks
   - list submissions
   - extract review content
   - create plan
   - submit plan

3. 让每个命令都能独立运行
   - 命令输入明确。
   - 输出适合大模型读取。
   - 不依赖长期终端交互。

4. 所有真实写操作都先 dry-run
   - 先保存计划文件。
   - 让用户确认。
   - 再提交。

5. 提交后必须核对
   - 重新拉页面或接口。
   - 比对实际结果。
   - 报告 mismatch。

6. 最后再写 skill
   - skill 写流程和边界。
   - 脚本做确定性动作。
   - 不要把不稳定功能写进 skill。

## 后续恢复考试功能时怎么做

考试当前已屏蔽。以后恢复时，不应该只打开考试 URL，而要补完整流程：

1. 确定考试列表接口或页面结构。
2. 获取考试列表，而不是只进入考试首页。
3. 明确用户能做哪些考试任务，例如查看考试、发布考试、批阅考试。
4. 处理浏览器登录态和课程上下文。
5. 做只读测试。
6. 确认不会误发布、误修改考试。
7. 再把 `TASK_ORDER` 改回包含 `exam`。
8. 更新 `chaoxing-teacher` skill。

## 本次最大的几个经验

1. API 优先，浏览器兜底。
2. 不要用终端菜单冒充大模型交互。
3. 不要一开始就写 skill，先稳定流程。
4. 打分必须先生成计划，再确认提交。
5. 真实提交后必须核对页面结果。
6. 内容审阅比随机分数更符合教师场景。
7. 附件解析是核心难点，尤其要区分题目附件和学生附件。
8. 考试这类高风险功能没稳定前应隐藏。
