#!/usr/bin/env python
# coding: utf-8


import mysql.connector
import pandas as pd
import numpy as np
import re
from datetime import timedelta



def connect_to_mysql(database):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database=database
    )
    return conn

# 从MySQL中检索数据
def fetch_data_from_mysql(conn, table_name):
    query = "SELECT * FROM {}".format(table_name)
    df = pd.read_sql(query, conn)
    return df




# 读取数据
conn = connect_to_mysql('sakai_bug')
df_issues = fetch_data_from_mysql(conn, 'issuesbugs')
conn.close()
print('数据条数：', df_issues.shape[0])



filtered_df = df_issues[df_issues['issuestatus'].isin(['Resolved','Closed','Verified','Awaiting Review'])]
filtered_df2 = filtered_df[filtered_df['resolution'].isin(['Fixed','Done'])]
conn = connect_to_mysql('sakai_bug')
df_commits = fetch_data_from_mysql(conn, 'github_commits')
conn.close()
print('数据条数：', df_commits.shape[0])
cleaned_df = df_commits.drop_duplicates(subset=['message','files'])



# 筛选回退的commit
revert_keywords = ['revert', 'Revert','reverting','undo']
filtered_messages = cleaned_df[~(cleaned_df['message'].str.contains('|'.join(revert_keywords)))]



def extract_issue_key(message):
    match = re.search(r'SAK-\d+', message)  # 使用正则表达式来匹配 "MDL-" 格式的 issue key
    if match:
        return match.group()  # 返回匹配到的 issue key
    else:
        return None



filtered_messages.loc[:,'issuekey'] = filtered_messages_cpy['message'].apply(extract_issue_key)



merged_df = pd.merge(filtered_messages, filtered_df2, on='issuekey', how='inner')
print('拼接后的commit数据条数：', merged_df.shape[0])



filtered_messages3 = filtered_messages[filtered_messages.issuekey.isin(merged_df.issuekey)]
filtered_df3 = filtered_df2[filtered_df2.issuekey.isin(merged_df.issuekey)]
filtered_df4 = filtered_df3.copy()
filtered_df4.replace(np.nan, None, inplace=True)
merged_df1 = merged_df.copy()
merged_df1.replace(np.nan, None, inplace=True)




conn = connect_to_mysql('sakai_bug')
cursor = conn.cursor()

# 将 DataFrame 中的数据插入到 MySQL 数据库中
for index, row in filtered_df4.iterrows():
    sql = "INSERT INTO issuesbugs_used(issueid, issueself, issuekey, fixversions, summary, project, issuetype, issuestatus, priority, versions, issuelinks, subtasks, resolution, assignee, labels, components, creator, reporter, timespent, created, updated, resolutiondate, description, comments, watchcount) VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s)"
    cursor.execute(sql, tuple(row))

# 提交事务
conn.commit()

cursor.close()
conn.close()



conn = connect_to_mysql('sakai_bug')
cursor = conn.cursor()

# 假设 df 是从 MySQL 数据库中读取的 DataFrame

# 将 DataFrame 中的数据插入到 MySQL 数据库中
for index, row in filtered_messages3.iterrows():
    sql = "INSERT INTO github_commits_used(sha, oid, author, created, committer, committed, message, commentcount, verified, reason, total, additions, deletions, changefiles, files, issuekey) VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor.execute(sql, tuple(row))

# 提交事务
conn.commit()

cursor.close()
conn.close()



conn = connect_to_mysql('sakai_bug')
cursor = conn.cursor()

# 假设 df 是从 MySQL 数据库中读取的 DataFrame

# 将 DataFrame 中的数据插入到 MySQL 数据库中
for index, row in merged_df1.iterrows():
    sql = "INSERT INTO issuesbugsandcommit(sha, oid, commitauthor, commitcreated, commitcommitter, committed, commitmessage, commentcount, verified, reason, total, additions, deletions, changefiles, files, issuekey, issueid, issueself, fixversions, summary, project, issuetype, issuestatus, priority, versions, issuelinks, subtasks, resolution, assignee, labels, components, creator, reporter, timespent, created, updated, resolutiondate, description, comments, watchcount) VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor.execute(sql, tuple(row))

# 提交事务
conn.commit()

cursor.close()
conn.close()

