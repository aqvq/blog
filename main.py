# -*- coding: utf-8 -*-
import argparse
import os
import re

import markdown
from feedgen.feed import FeedGenerator
from github import Github
from github.Issue import Issue
from github.Repository import Repository
import codecs

import urllib
from lxml.etree import CDATA
from marko.ext.gfm import gfm as marko
import time

BACKUP_DIR = "BACKUP"
MAX_PREVIEW_WORDS = 100
MAX_NEW_CREATES_NUM = 5
NAME = "Juzaizai"
EMAIL = "2505940811@qq.com"
LABEL_TOP = ":+1:置顶"
LABEL_COVER = ":framed_picture:封面"


def get_me(user):
    return user.get_user().login


def is_me(issue, me):
    return issue.user.login == me


# help to covert xml vaild string
def _valid_xml_char_ordinal(c):
    codepoint = ord(c)
    # conditions ordered by presumed frequency
    return (
        0x20 <= codepoint <= 0xD7FF
        or codepoint in (0x9, 0xA, 0xD)
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def login(token):
    return Github(token)

def get_repo(user: Github, repo: str):
    return user.get_repo(repo)


def generate_rss_feed(repo, filename, me):
    generator = FeedGenerator()
    generator.id(repo.html_url)
    generator.title(f"RSS feed of {repo.owner.login}'s {repo.name}")
    generator.author(
        {"name": os.getenv("GITHUB_NAME"), "email": os.getenv("GITHUB_EMAIL")}
    )
    generator.link(href=repo.html_url)
    generator.link(
        href=f"https://raw.githubusercontent.com/{get_username()}/{get_repo_name()}/main/{filename}",
        rel="self",
    )
    for issue in repo.get_issues():
        if not issue.body or not is_me(issue, me) or issue.pull_request:
            continue
        item = generator.add_entry(order="append")
        item.id(issue.html_url)
        item.link(href=issue.html_url)
        item.title(issue.title)
        item.published(issue.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"))
        for label in issue.labels:
            item.category({"term": label.name})
        body = "".join(c for c in issue.body if _valid_xml_char_ordinal(c))
        item.content(CDATA(marko.convert(body)), type="html")
    generator.atom_file(filename)


def get_time(only_date: bool = True):
    import pytz, datetime

    # 获取东八区的时间
    cst_timezone = pytz.timezone("Asia/Shanghai")
    curr_time = datetime.datetime.now(cst_timezone)  # 2024-11-26 11:39:19.871490+08:00
    curr_time = curr_time.replace(microsecond=0)
    curr_time = curr_time.replace(tzinfo=None)

    if only_date:
        return curr_time.strftime("%Y-%m-%d")
    else:
        return curr_time.strftime("%Y-%m-%d %H:%M:%S")  # 2024-11-26 11:39:19


def get_username():
    github_repo_env = os.environ.get("GITHUB_REPOSITORY")
    username = github_repo_env[0 : github_repo_env.index("/")]
    return username


def get_repo_name():
    github_repo_env = os.environ.get("GITHUB_REPOSITORY")
    repo_name = github_repo_env[github_repo_env.index("/") :]
    return repo_name


def main(token, repo_name, issue_number=None, dir_name=BACKUP_DIR):
    user = login(token)
    me = get_me(user)
    gitblog = get_repo(user, repo_name)
    print(f"user name: {get_username()}")
    print(f"repo name: {get_repo_name()}")
    print("login successfully!!!")

    # generate readme.md
    header_section = bundle_header_section(gitblog)
    summary_section = bundle_summary_section(gitblog)
    pinned_issues_section = bundle_pinned_issues_section(gitblog)
    new_created_section = bundle_new_created_section(gitblog, MAX_NEW_CREATES_NUM)
    list_by_labels_section = bundle_list_by_labels_section(gitblog)
    cover_image_section = bundle_cover_image_section(gitblog)
    # projects_section = bundle_projects_section()
    contents = [
        summary_section,
        cover_image_section,
        header_section,
        pinned_issues_section,
        new_created_section,
        list_by_labels_section,
    ]
    update_readme_md_file(contents)
    print("README.md updated successfully!!!")

    # generate rss
    generate_rss_feed(gitblog, "feed.xml", me)
    print("rss feed updated successfully!!!")


def format_issue(issue: Issue):
    return "- [%s](%s)  %s  \t \n" % (
        issue.title,
        issue.html_url,
        sup("%s :speech_balloon:" % issue.comments),
    )


def sup(text: str):
    return "<sup>%s</sup>" % text


def sub(text: str):
    return "<sub>%s</sub>" % text


def update_readme_md_file(contents):
    with codecs.open("README.md", "w", encoding="utf-8") as f:
        f.writelines(contents)
        f.flush()
        f.close()


def bundle_header_section():
    content = f"""
## [{NAME}'s BLOG](https://github.com/{get_username()}/{get_repo_name()})

My personal blog using issues and GitHub Actions! [RSS Feed](https://raw.githubusercontent.com/{get_username()}/{get_repo_name()}/main/feed.xml) 

### Hello World! Hello You! 😄  <image align="right" src="https://github-readme-stats.vercel.app/api?username={get_username()}&show_icons=true&hide_title=true&theme=gradient" />

🔭 I’m {NAME}

📫 Email: {EMAIL}

🌱 I’m currently learning Embodied AI

"""
    return content


def bundle_summary_section(repo):
    total_label_count = repo.get_labels().totalCount
    summary_section = """

<p align='center'>
    <img src="https://badgen.net/badge/labels/{2}"/>
    <img src="https://badgen.net/github/issues/{0}/{1}"/>
    <img src="https://badgen.net/badge/last-commit/{3}"/>
    <img src="https://badgen.net/github/forks/{0}/{1}"/>
    <img src="https://badgen.net/github/stars/{0}/{1}"/>
    <img src="https://badgen.net/github/watchers/{0}/{1}"/>
    <img src="https://badgen.net/github/release/{0}/{1}"/>
</p>

""".format(
        get_username(), get_repo_name(), total_label_count, get_time()
    )

    return summary_section


def generate_random_color():
    # 生成随机颜色的十六进制表示
    import random

    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def bundle_pinned_issues_section(repo):
    pinned_label = repo.get_label(LABEL_TOP)
    pinned_issues = repo.get_issues(labels=(pinned_label,))

    pinned_issues_section = "\n## 置顶 :thumbsup: \n"

    for issue in pinned_issues:
        pinned_issues_section += format_issue(issue)

    return pinned_issues_section


def format_issue_with_labels(issue: Issue):
    labels = issue.get_labels()
    labels_str = ""

    for label in labels:
        labels_str += "[%s](https://github.com/%s/%s/labels/%s), " % (
            label.name,
            get_username(),
            get_repo_name(),
            urllib.parse.quote(label.name),
        )

    if not issue.body:
        return ""
    if "---" in issue.body:
        body_summary = issue.body[: issue.body.index("---")]
    else:
        body_summary = issue.body[:MAX_PREVIEW_WORDS]
        # 如果前150个字符中有代码块，则在 150 个字符中重新截取代码块之前的部分作为 summary
    if "```" in body_summary:
        body_summary = body_summary[: body_summary.index("```")]

    return """
#### [{0}]({1}) {2} {3}

{4}

{5}

[更多>>>]({1})

---

""".format(
        issue.title,
        issue.html_url,
        sup("%s :speech_balloon:" % issue.comments),
        sup("%s :calendar:" % issue.created_at),
        ":label:".join(labels_str[:-2]),
        body_summary,
    )


def bundle_new_created_section(repo, nums: int = 5):
    filtered_labels = list(repo.get_labels())
    filtered_labels.remove(LABEL_COVER)
    filtered_labels.remove(LABEL_TOP)
    new_created_issues = repo.get_issues(labels=filtered_labels)[:nums]
    new_created_section = "## 最新 :new: \n"

    for issue in new_created_issues:
        new_created_section += format_issue_with_labels(issue)

    return new_created_section


def bundle_list_by_labels_section(repo):
    # word cloud

    list_by_labels_section = """
## 分类  :card_file_box: 
<details>
    <summary>
        Details
    </summary>

"""

    all_labels = repo.get_labels()

    for label in all_labels:
        temp = ""
        # TODO 这里的count是用来计算该label下有多少issue的, 按理说应该是取issues_in_label的totalCount, 但是不知道为什么取出来的一直都是
        # 所有的issue数量, 之后再优化.
        count = 0
        issues_in_label = repo.get_issues(labels=(label,))
        for issue in issues_in_label:
            temp += format_issue(issue)
            count += 1

        list_by_labels_section += """
<details>
<summary>%s\t<sup>%s:page_facing_up:</sup></summary>

%s

</details>
""" % (
            label.name,
            count,
            temp,
        )

    list_by_labels_section += """

</details>    
"""
    return list_by_labels_section


def bundle_cover_image_section(repo) -> str:
    cover_label = repo.get_label(LABEL_COVER)
    if cover_label is None:
        return ""
    cover_issues = repo.get_issues(labels=(cover_label,))
    if cover_issues is None or cover_issues.totalCount == 0:
        return ""
    comments = cover_issues[0].get_comments()
    if comments is None or comments.totalCount == 0:
        return ""
    c = comments[comments.totalCount - 1]
    img_md = None
    img_desc = ""
    if "---" in c.body:
        img_md = c.body.split("---")[0]
        img_desc = c.body.split("---")[1]
    else:
        img_md = c.body
    if img_md is None:
        return ""
    img_url = img_md[(img_md.index("(") + 1) : img_md.index(")")]
    print(img_url)
    return """

<p align='center'>
<a href='{0}'>
<img src='{1}' width='50%' alt='{2}'>
</a>
</p>
<p align='center'>
<span>{2}</span>
</p>

""".format(
        c.html_url, img_url, img_desc
    )


if __name__ == "__main__":
    if not os.path.exists(BACKUP_DIR):
        os.mkdir(BACKUP_DIR)
    parser = argparse.ArgumentParser()
    parser.add_argument("github_token", help="github_token")
    parser.add_argument("repo_name", help="repo_name")
    options = parser.parse_args()
    main(options.github_token)
