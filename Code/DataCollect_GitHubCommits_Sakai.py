#!/usr/bin/env python
# coding: utf-8



import os
import time
import mysql.connector
import requests
import json
import datetime
from dotenv import load_dotenv




# Your GitHub personal access token
load_dotenv(override = True)
GitHub_token = os.getenv("GITHUB_TOKEN")

# 设置请求头部信息，包括授权令牌
headers = {'Authorization': 'Bearer ' + GitHub_token}




# GitHub repository details
owner = 'sakaiproject'
repo = 'sakai'

# 每页返回的提交数量
per_page = 1000

# 初始化页数
page = 1

commit_shas = []

# 构建 API 请求的 URL
url = f"https://api.github.com/repos/{owner}/{repo}/commits?page={page}&per_page={per_page}"




# 发送 HTTP GET 请求，并初始化存储所有提交的列表
while True:
    # 发送 HTTP GET 请求
    response = requests.get(url,headers=headers)

    if response.status_code == 200:
        commits = response.json()
        if len(commits) == 0:
            print('finish!!!')
            # 如果返回的提交列表为空，则表示已经获取了所有的提交信息，退出循环
            break
        else:
            # 将返回的提交信息添加到存储所有提交的列表中
            for commit in commits:
                if commit['commit']['message'].find('SAK-')!=-1:
                    commit_shas.append(commit['sha'])
            # 更新下一页的 URL
            page += 1
            if page % 10 == 0:
                time.sleep(5)
            url = f"https://api.github.com/repos/{owner}/{repo}/commits?page={page}&per_page={per_page}"
    else:
        print("Failed to retrieve commit information. Status code:", response.status_code)
        break




mysql_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '123456',
        'database': 'sakai_bug'
    }




# GitHub 存储库的所有者和名称
owner = 'sakaiproject'
repo = 'sakai'

j = 0
while j < len(commit_shas):
    i = j
    j = j + 200
    all_commits = []
    # 循环遍历每个提交的 SHA
    while i < j and i < len(commit_shas):
        # 构建 API 请求的 URL
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_shas[i]}"

        # 发送 HTTP GET 请求
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            commit = response.json()
            all_commits.append(commit)
        else:
            print(f"Failed to retrieve commit information for SHA {commit_shas[i]}. Status code:", response.status_code)
        i = i + 1
    time.sleep(3)
#     print('此时i值：', i)
    
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
    for commit_info in all_commits:
        sha = commit_info['sha']
        oid = commit_info['node_id']
        author = commit_info['commit']['author']['name']
        created = datetime.datetime.strptime(commit_info['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ') if commit_info['commit']['author']['date'] else None
        committer = commit_info['commit']['committer']['name']
        committed = datetime.datetime.strptime(commit_info['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') if commit_info['commit']['committer']['date'] else None
        message = commit_info['commit']['message']
        commentcount = commit_info['commit']['comment_count']
        verified = commit_info['commit']['verification']['verified']
        reason = commit_info['commit']['verification']['reason']
        total = commit_info['stats']['total']
        additions = commit_info['stats']['additions']
        deletions = commit_info['stats']['deletions']
        changefiles = len(commit_info['files'])
        files = json.dumps([{'sha': dic['sha'], 'filename': dic['filename'], 'status': dic['status'], 'additions': dic['additions'], 'deletions': dic['deletions'], 'changes': dic['changes']} for dic in commit_info['files']])

        insert_query = "INSERT INTO github_commits(sha, oid, author, created, committer, committed, message, commentcount, verified, reason, total, additions, deletions, changefiles, files) VALUES ( %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (sha, oid, author, created, committer, committed, message, commentcount, verified, reason, total, additions, deletions, changefiles, files))
        conn.commit()
    cursor.close()
    conn.close()

