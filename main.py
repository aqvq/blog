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
from nasa_client import NasaClient

import urllib
from lxml.etree import CDATA
from marko.ext.gfm import gfm as marko
import time

MD_HEAD = ""
try:
    with open("header.md") as f:
        MD_HEAD = f.read()
except FileNotFoundError:
    print("Warning: 'header.md' not found. Using empty header.")

BACKUP_DIR = "BACKUP"
ANCHOR_NUMBER = 5
TOP_ISSUES_LABELS = ["Top"]
TODO_ISSUES_LABELS = ["TODO"]
FRIENDS_LABELS = ["Friends"]
ABOUT_LABELS = ["About"]
IGNORE_LABELS = FRIENDS_LABELS + TOP_ISSUES_LABELS + TODO_ISSUES_LABELS + ABOUT_LABELS

cur_time: str
gitblog = None

FRIENDS_TABLE_HEAD = "| Name | Link | Desc | \n | ---- | ---- | ---- |\n"
FRIENDS_TABLE_TEMPLATE = "| {name} | {link} | {desc} |\n"
FRIENDS_INFO_DICT = {
    "名字": "",
    "链接": "",
    "描述": "",
}


def get_me(user):
    return user.get_user().login


def is_me(issue, me):
    return issue.user.login == me


def is_hearted_by_me(comment, me):
    reactions = list(comment.get_reactions())
    for r in reactions:
        if r.content == "heart" and r.user.login == me:
            return True
    return False


def _make_friend_table_string(s):
    info_dict = FRIENDS_INFO_DICT.copy()
    try:
        string_list = s.splitlines()
        # drop empty line
        string_list = [l for l in string_list if l and not l.isspace()]
        for l in string_list:
            string_info_list = re.split("：", l)
            if len(string_info_list) < 2:
                continue
            info_dict[string_info_list[0]] = string_info_list[1]
        return FRIENDS_TABLE_TEMPLATE.format(
            name=info_dict["名字"], link=info_dict["链接"], desc=info_dict["描述"]
        )
    except Exception as e:
        print(str(e))
        return


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


def format_time(time):
    return str(time)[:10]


def login(token):
    return Github(token)


def get_repo(user: Github, repo: str):
    return user.get_repo(repo)


def parse_TODO(issue):
    body = issue.body.splitlines()
    todo_undone = [l for l in body if l.startswith("- [ ] ")]
    todo_done = [l for l in body if l.startswith("- [x] ")]
    # just add info all done
    if not todo_undone:
        return f"[{issue.title}]({issue.html_url}) all done", []
    return (
        f"[{issue.title}]({issue.html_url}) -- {len(todo_undone)} job(s) to do, {len(todo_done)} job(s) done",
        todo_done + todo_undone,
    )


def get_top_issues(repo):
    return repo.get_issues(labels=TOP_ISSUES_LABELS)


def get_todo_issues(repo):
    return repo.get_issues(labels=TODO_ISSUES_LABELS)


def get_repo_labels(repo):
    return [l for l in repo.get_labels()]


def get_issues_from_label(repo, label):
    return repo.get_issues(labels=(label,))


def add_issue_info(issue, md):
    time = format_time(issue.created_at)
    md.write(f"- {time} | [{issue.title}]({issue.html_url})\n")


def add_md_todo(repo, md, me):
    todo_issues = list(get_todo_issues(repo))
    if not TODO_ISSUES_LABELS or not todo_issues:
        return
    with open(md, "a+", encoding="utf-8") as md:
        md.write("## TODO\n")
        for issue in todo_issues:
            if is_me(issue, me):
                todo_title, todo_list = parse_TODO(issue)
                md.write("TODO list from " + todo_title + "\n")
                for t in todo_list:
                    md.write(t + "\n")
                # new line
                md.write("\n")


def add_md_top(repo, md, me):
    top_issues = list(get_top_issues(repo))
    if not TOP_ISSUES_LABELS or not top_issues:
        return
    with open(md, "a+", encoding="utf-8") as md:
        md.write("## 置顶文章\n")
        for issue in top_issues:
            if is_me(issue, me):
                add_issue_info(issue, md)


def add_md_firends(repo, md, me):

    s = FRIENDS_TABLE_HEAD
    friends_issues = list(repo.get_issues(labels=FRIENDS_LABELS))
    if not FRIENDS_LABELS or not friends_issues:
        return
    friends_issue_number = friends_issues[0].number
    for issue in friends_issues:
        for comment in issue.get_comments():
            if is_hearted_by_me(comment, me):
                try:
                    s += _make_friend_table_string(comment.body or "")
                except Exception as e:
                    print(str(e))
                    pass
    s = markdown.markdown(s, output_format="html", extensions=["extra"])
    with open(md, "a+", encoding="utf-8") as md:
        md.write(
            f"## [友情链接](https://github.com/{str(me)}/{str(me)}/issues/{friends_issue_number})\n"
        )
        md.write("<details><summary>显示</summary>\n")
        md.write(s)
        md.write("</details>\n")
        md.write("\n\n")


def add_md_recent(repo, md, me, limit=5):
    count = 0
    with open(md, "a+", encoding="utf-8") as md:
        # one the issue that only one issue and delete (pyGitHub raise an exception)
        try:
            md.write("## 最近更新\n")
            for issue in repo.get_issues():
                if is_me(issue, me):
                    add_issue_info(issue, md)
                    count += 1
                    if count >= limit:
                        break
        except Exception as e:
            print(str(e))


def add_md_header(md, repo_name):
    with open(md, "w", encoding="utf-8") as md:
        md.write(MD_HEAD.format(repo_name=repo_name))
        md.write("\n")




def add_md_label(repo, md, me):
    labels = get_repo_labels(repo)

    # sort lables by description info if it exists, otherwise sort by name,
    # for example, we can let the description start with a number (1#Java, 2#Docker, 3#K8s, etc.)
    labels = sorted(
        labels,
        key=lambda x: (
            x.description is None,
            x.description == "",
            x.description,
            x.name,
        ),
    )

    with open(md, "a+", encoding="utf-8") as md:
        for label in labels:
            # we don't need add top label again
            if label.name in IGNORE_LABELS:
                continue

            issues = get_issues_from_label(repo, label)
            if issues.totalCount:
                md.write("## " + label.name + "\n")
                issues = sorted(issues, key=lambda x: x.created_at, reverse=True)
            i = 0
            for issue in issues:
                if not issue:
                    continue
                if is_me(issue, me):
                    if i == ANCHOR_NUMBER:
                        md.write("<details><summary>显示更多</summary>\n")
                        md.write("\n")
                    add_issue_info(issue, md)
                    i += 1
            if i > ANCHOR_NUMBER:
                md.write("</details>\n")
                md.write("\n")


def get_to_generate_issues(repo, dir_name, issue_number=None):
    md_files = os.listdir(dir_name)
    generated_issues_numbers = [
        int(i.split("_")[0]) for i in md_files if i.split("_")[0].isdigit()
    ]
    to_generate_issues = [
        i
        for i in list(repo.get_issues())
        if int(i.number) not in generated_issues_numbers
    ]
    if issue_number:
        to_generate_issues.append(repo.get_issue(int(issue_number)))
    return to_generate_issues


def generate_rss_feed(repo, filename, me):
    generator = FeedGenerator()
    generator.id(repo.html_url)
    generator.title(f"RSS feed of {repo.owner.login}'s {repo.name}")
    generator.author(
        {"name": os.getenv("GITHUB_NAME"), "email": os.getenv("GITHUB_EMAIL")}
    )
    generator.link(href=repo.html_url)
    generator.link(
        href=f"https://raw.githubusercontent.com/{repo.full_name}/main/{filename}",
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


def main(token, repo_name, issue_number=None, dir_name=BACKUP_DIR):
    global gitblog
    user = login(token)
    me = get_me(user)
    gitblog = get_repo(user, repo_name)
    print("login successfully!!!")

    global cur_time
    # common
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # generate readme.md
    header_section = bundle_header_section()
    summary_section = bundle_summary_section()
    pinned_issues_section = bundle_pinned_issues_section()
    new_created_section = bundle_new_created_section()
    list_by_labels_section = bundle_list_by_labels_section()
    cover_image_section = bundle_cover_image_section()
    projects_section = bundle_projects_section()
    contents = [summary_section, header_section, cover_image_section, pinned_issues_section, new_created_section,
                list_by_labels_section, projects_section]
    update_readme_md_file(contents)
    print('README.md updated successfully!!!')
    
    # add to readme one by one, change order here
    # add_md_header("README.md", repo_name)
    # for func in [add_md_firends, add_md_top, add_md_recent, add_md_label, add_md_todo]:
    #     func(repo, "README.md", me)

    # generate rss
    generate_rss_feed(gitblog, "feed.xml", me)
    print("rss feed updated successfully!!!")
    
    # backup issues
    to_generate_issues = get_to_generate_issues(gitblog, dir_name, issue_number)
    for issue in to_generate_issues:
        save_issue(issue, me, dir_name)
    print("issues backup successfully!!!")

def save_issue(issue, me, dir_name=BACKUP_DIR):
    md_name = os.path.join(
        dir_name, f"{issue.number}_{issue.title.replace('/', '-').replace(' ', '.')}.md"
    )
    with open(md_name, "w") as f:
        f.write(f"# [{issue.title}]({issue.html_url})\n\n")
        f.write(issue.body or "")
        if issue.comments:
            for c in issue.get_comments():
                if is_me(c, me):
                    f.write("\n\n---\n\n")
                    f.write(c.body or "")


def format_issue(issue: Issue):
    return '- [%s](%s)  %s  \t \n' % (
        issue.title, issue.html_url, sup('%s :speech_balloon:' % issue.comments))


def sup(text: str):
    return '<sup>%s</sup>' % text


def sub(text: str):
    return '<sub>%s</sub>' % text


def update_readme_md_file(contents):
    with codecs.open('README.md', 'w', encoding='utf-8') as f:
        f.writelines(contents)
        f.flush()
        f.close()


# def login():
#     global user, username
#     github_repo_env = os.environ.get('GITHUB_REPOSITORY')
#     username = github_repo_env[0:github_repo_env.index('/')]
#     password = os.environ.get('GITHUB_TOKEN')
#     user = Github(username, password)


# def get_gitblog():
#     global gitblog
#     gitblog = user.get_repo(os.environ.get('GITHUB_REPOSITORY'))

def bundle_header_section():
    content = ""
    try:
        with open("header.md") as f:
            content = f.read()
    except FileNotFoundError:
        print("Warning: 'header.md' not found. Using empty header.")
    return content

def bundle_summary_section():
    global gitblog
    global cur_time
    global user
    global username

    total_label_count = gitblog.get_labels().totalCount
    total_issue_count = gitblog.get_issues().totalCount

    pic_of_the_day = NasaClient().get_picture_of_the_day()

    summary_section = '''

<p align='center'>
    <img src="https://badgen.net/badge/labels/{1}"/>
    <img src="https://badgen.net/github/issues/{0}/gitblog"/>
    <img src="https://badgen.net/badge/last-commit/{2}"/>
    <img src="https://badgen.net/github/forks/{0}/gitblog"/>
    <img src="https://badgen.net/github/stars/{0}/gitblog"/>
    <img src="https://badgen.net/github/watchers/{0}/gitblog"/>
    <img src="https://badgen.net/github/release/{0}/gitblog"/>
</p>

<p align='center'>
    <a href="https://github.com/jwenjian/visitor-count-badge">
        <img src="https://visitor-badge.glitch.me/badge?page_id=jwenjian.gitblog"/>
    </a>
</p>

'''.format(username, total_label_count, cur_time)

    return summary_section


def bundle_pinned_issues_section():
    global gitblog

    pinned_label = gitblog.get_label(':+1:置顶')
    pinned_issues = gitblog.get_issues(labels=(pinned_label,))

    pinned_issues_section = '\n## 置顶 :thumbsup: \n'

    for issue in pinned_issues:
        pinned_issues_section += format_issue(issue)

    return pinned_issues_section


def format_issue_with_labels(issue: Issue):
    global user, username

    labels = issue.get_labels()
    labels_str = ''

    for label in labels:
        labels_str += '[%s](https://github.com/%s/gitblog/labels/%s), ' % (
            label.name, username, urllib.parse.quote(label.name))

    if '---' in issue.body:
        body_summary = issue.body[:issue.body.index('---')]
    else:
        body_summary = issue.body[:150]
        # 如果前150个字符中有代码块，则在 150 个字符中重新截取代码块之前的部分作为 summary
        if '```' in body_summary:
            body_summary = body_summary[:body_summary.index('```')]

    return '''
#### [{0}]({1}) {2} \t {3}

:label: : {4}

{5}

[更多>>>]({1})

---

'''.format(issue.title, issue.html_url, sup('%s :speech_balloon:' % issue.comments), issue.created_at, labels_str[:-2],
           body_summary)


def bundle_new_created_section():
    global gitblog

    new_5_created_issues = gitblog.get_issues()[:5]

    new_created_section = '## 最新 :new: \n'

    for issue in new_5_created_issues:
        new_created_section += format_issue_with_labels(issue)

    return new_created_section


def bundle_list_by_labels_section():
    global gitblog
    global user

    # word cloud

    list_by_labels_section = """
<details open="open">
    <summary>
        ## 分类  :card_file_box: 
    </summary>

"""

    all_labels = gitblog.get_labels()

    for label in all_labels:
        temp = ''
        # 这里的count是用来计算该label下有多少issue的, 按理说应该是取issues_in_label的totalCount, 但是不知道为什么取出来的一直都是
        # 所有的issue数量, 之后再优化.
        count = 0
        issues_in_label = gitblog.get_issues(labels=(label,))
        for issue in issues_in_label:
            temp += format_issue(issue)
            count += 1

        list_by_labels_section += '''
<details>
<summary>%s\t<sup>%s:newspaper:</sup></summary>

%s

</details>
''' % (label.name, count, temp)

    list_by_labels_section += """

</details>    
"""
    return list_by_labels_section


def bundle_cover_image_section() -> str:
    global gitblog
    cover_label = gitblog.get_label(':framed_picture:封面')
    if cover_label is None:
        return ''
    cover_issues = gitblog.get_issues(labels=(cover_label,))
    if cover_issues is None or cover_issues.totalCount == 0:
        return ''
    comments = cover_issues[0].get_comments()
    if comments is None or comments.totalCount == 0:
        return ''
    c = comments[comments.totalCount - 1]
    img_md = None
    img_desc = ''
    if '---' in c.body:
        img_md = c.body.split('---')[0]
        img_desc = c.body.split('---')[1]
    else:
        img_md = c.body
    if img_md is None:
        return ''
    img_url = img_md[(img_md.index('(') + 1):img_md.index(')')]
    print(img_url)
    return '''

<p align='center'>
<a href='{0}'>
<img src='{1}' width='50%' alt='{2}'>
</a>
</p>
<p align='center'>
<span>{2}</span>
</p>

    '''.format(c.html_url, img_url, img_desc)


def bundle_projects_section() -> str:
    global gitblog, username
    project_label = gitblog.get_label('开源')
    if not project_label:
        return ''
    issues = gitblog.get_issues(labels=(project_label,))
    if not issues or issues.totalCount == 0:
        return ''
    content = ''
    for (idx, i) in enumerate(issues):
        content += '''
| [{1}](https://github.com/{0}/{1}) | {2} | ![](https://badgen.net/github/stars/{0}/{1}) ![](https://badgen.net/github/forks/{0}/{1}) ![](https://badgen.net/github/watchers/{0}/{1}) |'''.format(
            username, i.title, i.body)
        if idx == 0:
            content += '\n| --- | --- | --- |'
    return '''
# 开源项目

{}

'''.format(content)


def execute():
    pass


if __name__ == "__main__":
    if not os.path.exists(BACKUP_DIR):
        os.mkdir(BACKUP_DIR)
    parser = argparse.ArgumentParser()
    parser.add_argument("github_token", help="github_token")
    parser.add_argument("repo_name", help="repo_name")
    parser.add_argument(
        "--issue_number", help="issue_number", default=None, required=False
    )
    options = parser.parse_args()
    main(options.github_token, options.repo_name, options.issue_number)

