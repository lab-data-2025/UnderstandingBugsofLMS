#!/usr/bin/env python
# coding: utf-8



import os
import datetime
import pytz
import json
from jira import JIRA
import mysql.connector
from dateutil.parser import parse
from dotenv import load_dotenv




# Your JIRA account
load_dotenv(override = True)
username_Jira = os.getenv("JIRA_USERNAME")
password_Jira = os.getenv("JIRA_PASSWORD")




#获取bug issue
def getMyBug():
    jira = JIRA('https://tracker.moodle.org/', basic_auth=(username_Jira, password_Jira))
    jql = 'project = MDL AND issuetype = Bug'
    totalNum = jira.search_issues(jql).total
#     print(totalNum)
#     project = jira.projects()
#     print(project)

    starAt = 0
    issues = []
    # issues = jira.search_issues(jql, startAt=starAt, maxResults=10)
    while starAt < totalNum:
        issues.extend(jira.search_issues(jql, startAt=starAt, maxResults=100))
        starAt += 100
#     print(starAt)
    return issues

#将BUG导出到Mysql
def exportMysql(issues):
    # MySQL 数据库连接参数
    mysql_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '123456',
        'database': 'moodle_bug'
    }

    # 连接到MySQL数据库
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()

    i = 1
    for issue in issues:
        issueid = issue.id
        issueself = issue.self
        issuekey = issue.key
        fixversions = json.dumps([{"name": version.name, "id": version.id} for version in issue.fields.fixVersions])
        summary = issue.fields.summary
        project = issue.fields.project.name
        issuetype = issue.fields.issuetype.name
        issuestatus = issue.fields.status.name
        priority = issue.fields.priority.name if issue.fields.priority else None
        versions = json.dumps([{"name": version.name, "id": version.id} for version in issue.fields.versions])
        issuelinks = json.dumps([{"id":issuelink.id, "typename": issuelink.type.name, "inward":issuelink.type.inward, "outward":issuelink.type.outward, "inwardIssueid":issuelink.inwardIssue.id if hasattr(issuelink, "inwardIssue") else None, "outwardIssueid":issuelink.outwardIssue.id if hasattr(issuelink, "outwardIssue") else None} for issuelink in issue.fields.issuelinks])
        subtasks = json.dumps([{"id":subtask.id, "key":subtask.key, "summary": subtask.fields.summary} for subtask in issue.fields.subtasks])
        resolution = issue.fields.resolution.name if issue.fields.resolution else None
        assignee = issue.fields.assignee.displayName if issue.fields.assignee else None
        labels = json.dumps(issue.fields.labels)
        components = json.dumps([{"id":component.id, "name": component.name,"description":component.description if hasattr(component, "description") else None} for component in issue.fields.components])
        creator = issue.fields.creator.displayName if hasattr(issue.fields, "creator") else None
        reporter = issue.fields.reporter.displayName if issue.fields.reporter else None
        timespent = issue.fields.timespent
        created_time = datetime.datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z') if issue.fields.created else None
        created = created_time.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        updated_time = datetime.datetime.strptime(issue.fields.updated, '%Y-%m-%dT%H:%M:%S.%f%z') if issue.fields.updated else None
        updated = updated_time.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S') if updated_time else None
        resolutiondate_time = datetime.datetime.strptime(issue.fields.resolutiondate, '%Y-%m-%dT%H:%M:%S.%f%z') if issue.fields.resolutiondate else None
        resolutiondate = resolutiondate_time.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S') if resolutiondate_time else None
        description = issue.fields.description
        comments = json.dumps({"comments":[{"id":oneComment.id, "self":oneComment.self, "author": oneComment.author.displayName if hasattr(oneComment, "author") else None,"body":oneComment.body,"updateAuthor":oneComment.updateAuthor.displayName if hasattr(oneComment, "updateAuthor") else None,"created":oneComment.created,"updated":oneComment.updated} for oneComment in issue.fields.comment.comments],"maxResults": issue.fields.comment.maxResults, "total": issue.fields.comment.total, "startAt": issue.fields.comment.startAt})
        watchcount = issue.fields.watches.watchCount if issue.fields.watches else 0

        #执行插入数据的SQL语句
        insert_query = "INSERT INTO issuesbugs(issueid, issueself, issuekey, fixversions, summary, project, issuetype, issuestatus, priority, versions, issuelinks, subtasks, resolution, assignee, labels, components, creator, reporter, timespent, created, updated, resolutiondate, description, comments, watchcount) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s)"

        try:
            cursor.execute(insert_query, (issueid, issueself, issuekey, fixversions, summary, project, issuetype, issuestatus, priority, versions, issuelinks, subtasks, resolution, assignee, labels, components, creator, reporter, timespent, created, updated, resolutiondate, description, comments, watchcount))
            conn.commit()
        except:
            print("插入数据有误"+ str(i) + " issueid:" + str(issueid))
            conn.rollback()
        i += 1
        if i % 100 == 0:
            print("已插入" + str(i) + "条数据")

    # 提交事务并关闭连接
    cursor.close()
    conn.close()




#主程序
def main():
    issues = getMyBug()
    exportMysql(issues)

if __name__ == '__main__':
    main()

