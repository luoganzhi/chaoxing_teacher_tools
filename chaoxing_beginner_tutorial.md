---
title: 从零实现超星自动化工具：小白教程
created: 2026-05-31
updated: 2026-05-31
type: 教程
status: 可复用
project: 超星自动化工具
course: 人工智能应用基础
source_file: /Users/lgzyy/solo_work/chaoxing_tools/chaoxing_beginner_tutorial.md
tags:
  - 超星
  - 教学自动化
  - 作业批改
  - API逆向
  - Cookie登录
  - Python
  - 大模型评分
  - Obsidian教程
aliases:
  - 超星自动化工具小白教程
  - 超星作业批改自动化教程
  - Chaoxing 自动化开发教程
---

# 从零实现超星自动化工具：小白教程

这是一份面向初学者的教程。它不假设你已经熟悉 HTTP、cookie、API、浏览器开发者工具或 skill。

原来的文档：

```text
chaoxing_skill_development_walkthrough.md
```

保留为“工程复盘版”。这份文档是“从零学习版”。

## Obsidian 关联

- 所属课程：[[锦城学院/人工智能应用基础|人工智能应用基础]]
- 相关主题：[[教学自动化]]、[[超星自动化工具]]、[[大模型辅助批改]]、[[Cookie 登录]]、[[API 逆向分析]]
- 相关笔记：[[标签整理]]、[[学习/软件/开源项目|开源项目]]、[[锦城学院/人工智能应用基础/神经网络示例/环境安装指南|神经网络示例环境安装指南]]
- 工程目录：`/Users/lgzyy/solo_work/chaoxing_tools`
- 核心脚本：`chaoxing_portal_tool.py`

> [!important]
> 这份笔记涉及真实教学平台和成绩提交。学习时优先使用 dry-run，真实提交前必须让用户确认，提交后必须重新核对页面分数。

## 你最终会学会什么

学完后，你应该能理解并自己实现类似流程：

```text
登录超星 -> 保存 cookie -> 复用 cookie 请求接口
-> 获取教学课程 -> 获取班级 -> 获取作业
-> 获取待批学生 -> 获取学生提交内容
-> 生成评分计划 -> 用户确认 -> 提交分数 -> 核对结果
-> 写成 skill
```

## 学习前需要知道的事

这类自动化工具会访问真实教学系统，甚至可能提交真实分数。所以一定要遵守：

1. 不要把账号、密码、cookie 发给别人。
2. 不要把 `.chaoxing_cookies.json` 上传到公开仓库。
3. 所有提交分数动作必须先 dry-run。
4. 真实提交前必须让用户确认。
5. 提交后必须重新核对。
6. 不稳定功能先隐藏，不要写进 skill。

## 推荐学习路线

不要直接跳到完整脚本。按这个顺序学：

```text
第 1 课：理解网页请求
第 2 课：理解 cookie
第 3 课：用 requests 请求网页
第 4 课：保存和复用 cookie
第 5 课：用 DevTools 找接口
第 6 课：获取课程和班级
第 7 课：解析 HTML 页面
第 8 课：获取作业和待批学生
第 9 课：下载和解析学生附件
第 10 课：生成评分计划
第 11 课：提交并核对
第 12 课：封装成 skill
```

## 第 1 课：理解网页请求

你在浏览器里打开一个网页，本质上是浏览器向服务器发请求。

例如你打开：

```text
https://i.chaoxing.com/
```

浏览器会发一个请求：

```text
GET / HTTP/1.1
Host: i.chaoxing.com
Cookie: ...
User-Agent: ...
```

服务器返回：

```text
HTTP/1.1 200 OK
Content-Type: text/html

<html>...</html>
```

自动化工具要做的，就是用代码模拟浏览器请求。

### GET 和 POST

最常见两种请求：

```text
GET：获取数据，例如打开课程列表、作业列表。
POST：提交数据，例如登录、提交分数。
```

例子：

```text
GET  https://i.chaoxing.com/
POST https://passport2.chaoxing.com/fanyalogin
```

### 你需要记住

```text
浏览器能看到的内容，很多时候代码也能请求到。
关键是找到正确 URL、参数、cookie 和请求头。
```

## 第 2 课：理解 cookie

cookie 可以理解为“登录凭证”。

你输入账号密码登录成功后，服务器会给浏览器一些 cookie。之后浏览器访问课程、作业、批阅页面时，会自动带上这些 cookie。

服务器看到 cookie，就知道：

```text
这是已经登录的用户。
```

### 为什么自动化要保存 cookie

如果不保存 cookie，每次运行脚本都要重新登录。

保存 cookie 后：

```text
第一次：账号密码登录 -> 保存 cookie
以后：读取 cookie -> 直接请求接口
```

这就是自动化的基础。

### cookie 长什么样

不要看真实值，只看结构：

```json
{
  "name": "UID",
  "value": "敏感值，不要展示",
  "domain": ".chaoxing.com",
  "path": "/",
  "secure": false,
  "expires": 1780600640,
  "httpOnly": true
}
```

最重要的字段：

- `name`：名字。
- `value`：值，敏感。
- `domain`：在哪个域名生效。
- `path`：在哪个路径生效。
- `expires`：什么时候过期。

## 第 3 课：第一个 requests 请求

Python 里常用 `requests` 发 HTTP 请求。

安装依赖：

```bash
python3 -m pip install requests
```

新建一个最小脚本：

```python
import requests

url = "https://i.chaoxing.com/"
response = requests.get(url, timeout=20)

print(response.status_code)
print(response.url)
print(response.text[:200])
```

运行：

```bash
python3 test_request.py
```

如果没有 cookie，你大概率会看到登录页。

这很正常。下一课要解决 cookie。

## 第 4 课：保存和复用 cookie

我们用 `requests.Session()` 保存 cookie。

```python
import requests

session = requests.Session()
```

`Session` 的作用：

```text
第一次请求服务器返回 cookie 后，session 会记住。
之后 session 再请求其他页面，会自动带上 cookie。
```

### 保存 cookie

登录成功后，可以把 session 里的 cookie 存成 JSON：

```python
import json
import time
import os

def save_cookie_file(session, path):
    cookies = []
    for cookie in session.cookies:
        cookies.append({
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path,
            "secure": bool(cookie.secure),
            "expires": cookie.expires,
            "httpOnly": cookie.has_nonstandard_attr("HttpOnly"),
        })

    payload = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cookies": cookies,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    os.chmod(path, 0o600)
```

### 加载 cookie

```python
import json
import requests

def request_session_from_cookie_file(path):
    session = requests.Session()

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    for cookie in payload["cookies"]:
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie["domain"],
            path=cookie.get("path", "/"),
        )

    return session
```

然后你就可以这样请求：

```python
session = request_session_from_cookie_file(".chaoxing_cookies.json")
response = session.get("https://i.chaoxing.com/", timeout=20)
print(response.url)
print(response.text[:200])
```

### 检查是否登录

不能只看 cookie 文件是否存在。要访问一个登录后页面，看有没有跳登录。

最简单判断：

```python
def is_login_page(url, html):
    return "passport2.chaoxing.com" in url or "账号登录" in html or "手机号" in html
```

真实项目里可以更细：

```text
如果页面含“学习空间”“我的课程”，大概率已登录。
如果页面含“忘记密码”“手机号登录”，大概率未登录。
```

## 第 5 课：用 API 登录拿 cookie

现在讲真正登录。

人工登录是：

```text
打开登录页 -> 输入账号密码 -> 点击登录 -> 浏览器保存 cookie
```

API 登录是：

```text
代码请求登录页 -> 解析登录参数 -> 提交账号密码 -> session 保存 cookie
```

### 步骤 1：请求登录页

```python
LOGIN_PAGE_URL = "https://passport2.chaoxing.com/login"

session = requests.Session()
login_page = LOGIN_PAGE_URL + "?newversion=true&fid=1971&refer=https%3A%2F%2Fscujcc.fanya.chaoxing.com%2Fportal"

response = session.get(login_page, timeout=20)
html = response.text
```

### 步骤 2：解析 hidden input

登录页里可能有：

```html
<input type="hidden" name="fid" value="1971">
<input type="hidden" name="t" value="true">
```

写一个函数解析：

```python
import re
from html import unescape

def html_attrs(tag):
    return {
        name.lower(): unescape(value)
        for name, _quote, value in re.findall(
            r"([a-zA-Z_:][\w:.-]*)\s*=\s*(['\"])(.*?)\2",
            tag,
            flags=re.S,
        )
    }

def parse_hidden_inputs(html):
    hidden = {}
    for match in re.finditer(r"<input\b[^>]*>", html, flags=re.I | re.S):
        tag = match.group(0)
        attrs = html_attrs(tag)
        if attrs.get("type", "").lower() != "hidden":
            continue
        key = attrs.get("name") or attrs.get("id")
        if key:
            hidden[key] = attrs.get("value", "")
    return hidden
```

### 步骤 3：处理账号密码加密

超星登录页里 `t=true` 时，账号密码需要加密。

本项目使用：

```text
AES-CBC + PKCS7 + base64
```

这部分小白一开始不必完全理解密码学，只要知道：

```text
浏览器提交的不是明文密码，脚本要模拟浏览器的加密方式。
```

完整实现已经在：

```text
chaoxing_portal_tool.py -> aes_encrypt_base64()
```

### 步骤 4：POST 登录接口

登录接口：

```text
https://passport2.chaoxing.com/fanyalogin
```

提交数据：

```python
payload = {
    "fid": hidden.get("fid", "1971"),
    "uname": post_username,
    "password": post_password,
    "refer": hidden.get("refer", refer),
    "t": hidden.get("t", "true"),
    "forbidotherlogin": hidden.get("forbidotherlogin", "0"),
    "validate": hidden.get("validate", ""),
    "doubleFactorLogin": hidden.get("doubleFactorLogin", "0"),
    "independentId": hidden.get("independentId", ""),
    "independentNameId": hidden.get("independentNameId", ""),
}
```

请求：

```python
response = session.post(
    "https://passport2.chaoxing.com/fanyalogin",
    data=payload,
    headers={
        "Origin": "https://passport2.chaoxing.com",
        "Referer": login_page,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    },
    timeout=20,
)
result = response.json()
```

### 步骤 5：登录后 warmup

登录成功后不要马上保存 cookie。先访问返回的 URL 和目标门户页：

```python
target_url = result.get("url")
if target_url:
    session.get(target_url, allow_redirects=True, timeout=20)

session.get("https://scujcc.fanya.chaoxing.com/portal", allow_redirects=True, timeout=20)
```

原因：

```text
有些 cookie 是登录后跳转过程中设置的。
不 warmup，cookie 可能不完整。
```

最后保存：

```python
save_cookie_file(session, ".chaoxing_cookies.json")
```

## 第 6 课：用 DevTools 找接口

这是你以后自己实现别的平台时最重要的能力。

### 打开 Network

Chrome 里：

```text
右键页面 -> 检查 -> Network
```

勾选：

```text
Preserve log
Disable cache
```

然后按真实操作点页面。

### 找接口的顺序

例如你想找“课程列表接口”：

1. 清空 Network。
2. 刷新课程页。
3. 看新增请求。
4. 搜关键词：

```text
course
clazz
backclazz
mycourse
```

5. 点开请求，看 Response。
6. 如果 Response 是 JSON，并且里面有课程名和班级，就是目标接口。

本项目找到的是：

```text
https://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&rss=1
```

### Copy as cURL

Network 里右键请求：

```text
Copy -> Copy as cURL
```

把它粘贴到终端运行。

如果 curl 能返回同样内容，说明你已经找到了可复用请求。

然后你可以把 curl 改成 Python requests。

### 小白判断法

看到这些词，大概率是接口：

```text
api
json
list
data
query
mark-list
workinfo
status
```

看到这些词，大概率是静态资源：

```text
css
js
png
jpg
woff
svg
```

静态资源一般不用管。

## 第 7 课：获取教学课程

课程接口返回 JSON，所以比较简单。

```python
BACKCLAZZ_URL = "https://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&rss=1"

session = request_session_from_cookie_file(".chaoxing_cookies.json")
response = session.get(BACKCLAZZ_URL, timeout=20)
data = response.json()
```

你要从里面找：

```text
channelList
content
clazz
```

简单理解：

```text
channelList：课程容器列表
content：课程信息
clazz：班级列表
```

伪代码：

```python
courses = []

for channel in data["channelList"]:
    content = channel.get("content", {})
    clazzes = content.get("clazz")

    if not clazzes:
        continue

    courses.append({
        "course_id": content["id"],
        "course_name": content["name"],
        "teacher": content.get("teacherfactor", ""),
        "term": content.get("schools", ""),
        "cpi": channel.get("cpi") or content.get("cpi"),
        "classes": clazzes,
    })
```

为什么 `clazz` 重要：

```text
有 clazz 的课程才是教师可管理的课程。
```

## 第 8 课：获取班级并优先自己的班

课程里的 `clazz` 大概包含：

```json
{
  "clazzId": "140622283",
  "clazzName": "物联网2501-1班-某教师",
  "clazzStudentCount": 28
}
```

整理成：

```python
{
    "clazz_id": clazz["clazzId"],
    "clazz_name": clazz["clazzName"],
    "student_count": clazz.get("clazzStudentCount"),
}
```

要优先当前用户的班，需要先获取当前用户姓名。

访问：

```text
https://i.chaoxing.com/
```

然后从 HTML 里找用户信息。

如果班级名包含当前用户姓名：

```python
clazz["is_user_class"] = owner_name in clazz["clazz_name"]
```

排序：

```python
classes.sort(key=lambda c: 0 if c.get("is_user_class") else 1)
```

这样显示时用户自己的班就在前面。

## 第 9 课：从课程入口获取作业模块

只知道 `course_id` 和 `clazz_id` 还不够。超星课程页还需要：

```text
cpi
enc
openc
t
```

所以要先访问课程入口：

```text
https://mooc1.chaoxing.com/course/isNewCourse
```

参数：

```python
{
    "courseId": course_id,
    "clazzId": clazz_id,
    "edit": "true",
    "v": "2",
    "cpi": cpi,
    "pageHeader": "6",
    "single": "0",
}
```

返回的是 HTML。里面有 hidden input：

```html
<input type="hidden" name="courseid" value="...">
<input type="hidden" name="clazzid" value="...">
<input type="hidden" name="enc" value="...">
```

也有导航项：

```html
<li dataname="zy" pageheader="6">
  <a data-url="/mooc2-ans/work/list" title="作业">
</li>
```

所以你要解析两类内容：

```text
hidden input -> 拼接后续 URL 的参数
导航 data-url -> 作业模块真实路径
```

## 第 10 课：获取作业列表

作业列表 URL 大概是：

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list
```

参数来自上一步 hidden 字段：

```python
params = {
    "courseid": courseid,
    "clazzid": clazzid,
    "courseId": courseid,
    "classId": clazzid,
    "clazzId": clazzid,
    "cpi": cpi,
    "enc": enc,
    "openc": openc,
    "t": t,
    "ut": "t",
    "selectClassid": clazzid,
    "pages": "1",
    "pageSize": "12",
    "status": "-1",
}
```

返回 HTML。每个作业大概是一个：

```html
<li id="work53018076">
  ...
  11 待批 28 已交 0 未交
  ...
</li>
```

提取：

```python
work_id
title
pending_count
submitted_count
unsubmitted_count
```

如果 `pending_count > 0`，就是未批改作业。

## 第 11 课：获取待批学生

提交列表接口：

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark-list
```

参数：

```python
params = {
    "courseid": course_id,
    "clazzid": clazz_id,
    "workid": work_id,
    "submit": "true",
    "status": "3",
    "cpi": cpi,
    "pages": "1",
    "size": "100",
}
```

`status=3` 表示待批。

返回 HTML，每个学生一行：

```html
<ul class="dataBody_td" id="55478986">
  <div class="py_name">学生姓名</div>
  <input class="scoreInput" value="">
  <a data="/mooc2-ans/work/library/review-work?...">
</ul>
```

解析：

```python
answer_id = ul 的 id
student_name = py_name 里的文本
score = scoreInput 的 value
review_url = a 标签 data 属性
```

`review_url` 用来打开单个学生批阅页。

## 第 12 课：获取学生提交内容

对每个待批学生，请求：

```python
response = session.get(review_url, timeout=20, allow_redirects=True)
html = response.text
```

重点找学生答案区域：

```html
<dd class="stuAnswerWords">
  学生写的答案
  <iframe class="attach-iframe" filename="..." objectid="...">
</dd>
```

为什么只找 `stuAnswerWords`：

```text
整页可能包含题目附件。
只有学生答案区域里的附件才是学生提交物。
```

提取三类东西：

```text
文本答案
图片答案
附件 objectid
```

## 第 13 课：下载附件并抽取文本

附件 iframe 里通常没有直接下载链接，只有：

```text
objectid
filename
filetype
```

要先请求：

```text
https://mooc2-ans.chaoxing.com/ananas/status/{objectid}
```

这个接口返回：

```json
{
  "download": "http://d0.cldisk.com/download/..."
}
```

然后再下载 `download` URL。

注意请求头：

```python
headers = {
    "Referer": "https://mooc2-ans.chaoxing.com/",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}
```

没有这些头，可能 403。

### 抽取文本

按文件类型：

```text
docx -> python-docx
pdf  -> pdfplumber
txt/md/py/csv -> 直接读
zip -> 列文件名
```

docx 如果因为图片损坏读取失败，就兜底读：

```text
word/document.xml
```

因为 docx 本质是 zip 包，正文通常在这个 XML 里。

## 第 14 课：保存 review bundle

不要一边读学生作业一边直接打分。先保存一份 bundle：

```json
{
  "course": {},
  "selected_class": {},
  "homework": {},
  "reviews": [
    {
      "submission": {
        "answer_id": "...",
        "student_name": "..."
      },
      "summary": {
        "student_answer_attachments": []
      },
      "downloaded_assets": [
        {
          "filename": "...",
          "path": "...",
          "extracted_text": "..."
        }
      ]
    }
  ]
}
```

这样有三个好处：

1. 大模型可以反复审阅，不用重复下载。
2. 出错时可以检查中间结果。
3. 评分和提交分离，更安全。

## 第 15 课：让大模型生成评分 JSON

大模型阅读 `extracted_text` 后，生成：

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

评分规则：

```text
内容相关、完成度正常：尽量 70 分以上。
内容明显跑题、空白、无效：可以低于 70，但必须说明原因。
每个分数都要有 reason。
```

## 第 16 课：生成评分计划，不直接提交

评分 JSON 不能直接提交。要先生成 plan：

```bash
python3 chaoxing_portal_tool.py homework-grade-reviewed review_bundle.json review_scores.json
```

plan 里保存：

```text
course
class
homework
answer_id
student_name
score
reason
```

展示给用户：

```text
1. 学生A -> 90 | reason: ...
2. 学生B -> 87 | reason: ...
```

然后停下来，等用户说：

```text
提交分数
```

## 第 17 课：提交分数

提交接口：

```text
POST https://mooc2-ans.chaoxing.com/mooc2-ans/work/markscore
```

参数大致是：

```python
{
    "courseid": course_id,
    "clazzid": clazz_id,
    "cpi": cpi,
    "workid": work_id,
    "answerIds": answer_id,
    "type": "0",
    "score": score,
}
```

URL query 里也有：

```python
{
    "markScore": score,
    "markAnswerIds": answer_id,
    "markType": "0",
}
```

提交时按 plan 逐个学生提交。

## 第 18 课：提交后核对

不要只相信“操作成功”。

提交后重新请求：

```text
/mooc2-ans/work/mark-list?status=0
```

然后按 `answer_id` 比对：

```text
计划分数 == 页面实际分数
```

输出：

```text
expected=11
matched=11
mismatch=0
missing=0
```

只有 `mismatch=0` 且 `missing=0`，才算真正完成。

## 第 19 课：写成 skill

脚本稳定后，再写 skill。

skill 不需要复制所有代码。skill 写的是：

```text
什么时候触发
按什么流程调用脚本
哪些功能禁用
什么时候必须让用户确认
哪些安全边界不能越过
```

本项目 skill：

```text
/Users/lgzyy/.agents/skills/chaoxing-teacher/SKILL.md
```

核心规则：

```text
用户说“进入超星” -> 检查登录 -> 列课程
用户选课程 -> 列班级
用户选班级 -> 只显示作业
用户选作业 -> 查未批改
批改前 -> 先提取内容
提交前 -> 展示 plan 等确认
提交后 -> 核对
```

## 常见错误和解决方法

### 1. 请求跳到登录页

现象：

```text
final_url 是 passport2.chaoxing.com/login
```

原因：

```text
cookie 没有带上、cookie 过期、cookie 域名不对。
```

解决：

```bash
python3 chaoxing_portal_tool.py api-status
python3 chaoxing_portal_tool.py login
```

### 2. JSON 解析失败

现象：

```text
response.json() 报错
```

原因：

```text
接口返回的不是 JSON，可能是 HTML 登录页或错误页。
```

解决：

```python
print(response.url)
print(response.text[:500])
```

先看实际返回了什么。

### 3. 附件接口 403

原因：

```text
缺 Referer/User-Agent，或者网络沙箱限制。
```

解决：

```python
headers = {
    "Referer": "https://mooc2-ans.chaoxing.com/",
    "User-Agent": "Mozilla/5.0",
}
```

必要时放开网络权限。

### 4. 学生附件和题目附件混在一起

原因：

```text
直接解析整页 iframe。
```

解决：

```text
只解析 stuAnswerWords 里的附件。
```

### 5. 同名附件覆盖

解决：

```text
本地文件名前加：学生序号_学生名_
```

### 6. docx 读取失败

原因：

```text
docx 里的图片或媒体文件损坏。
```

解决：

```text
兜底读取 word/document.xml。
```

### 7. 模型准备直接提交分数

解决：

```text
禁止。必须先生成 plan，展示摘要，等用户明确确认。
```

## 小白练习路径

你可以按下面顺序练习，每一步都能单独完成。

### 练习 1：请求一个网页

目标：

```text
用 requests 打开 https://i.chaoxing.com/ 并打印 status_code。
```

### 练习 2：保存一个 cookie 文件

目标：

```text
理解 JSON cookie 文件结构，不需要真实登录。
```

### 练习 3：用 DevTools 找课程接口

目标：

```text
打开 Network，找到 backclazzdata 请求。
```

### 练习 4：请求课程接口

目标：

```text
用保存的 cookie 请求 backclazzdata，并打印课程名。
```

### 练习 5：解析作业列表 HTML

目标：

```text
保存一段 HTML 到文件，用正则提取 work_id 和待批数量。
```

### 练习 6：生成 dry-run 评分计划

目标：

```text
手写一个 review_scores.json，生成 grade_plan，不提交。
```

### 练习 7：理解提交核对

目标：

```text
读取 plan，模拟页面实际分数，比较 matched/mismatch。
```

## 最重要的思维方式

不要把自动化理解为“让程序乱点网页”。

更稳定的方式是：

```text
先理解浏览器发了什么请求
再用代码复现这个请求
再解析返回数据
最后把动作拆成可确认、可回滚、可核对的步骤
```

这就是本项目的核心。
