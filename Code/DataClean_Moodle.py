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
conn = connect_to_mysql('moodle_bug')
df_issues = fetch_data_from_mysql(conn, 'issuesbugs')
conn.close()
print('数据条数：', df_issues.shape[0])




unique_resolution = df_issues['resolution'].unique()
unique_status = df_issues['issuestatus'].unique()

print(unique_resolution)
print(unique_status)




filtered_df = df_issues[df_issues['issuestatus'].isin(['Waiting for feedback','Closed'])]

filtered_df2 = filtered_df[filtered_df['resolution'].isin(['Fixed','Done'])]




df_stable = filtered_df2[filtered_df2['created'] >= '2014-11-9']

print(df_stable.shape[0])




conn = connect_to_mysql('moodle_bug')
df_commits = fetch_data_from_mysql(conn, 'github_commits')
conn.close()
print('数据条数：', df_commits.shape[0])



duplicate_messages = df_commits['message'].duplicated()
cleaned_df = df_commits.drop_duplicates(subset=['message','files'])
revert_keywords = ['revert', 'Revert','reverting','undo']



# 将回退和提交重复的行筛选出来
filtered_messages = cleaned_df[~(cleaned_df['message'].str.contains('|'.join(revert_keywords)))]




def extract_issue_key(message):
    match = re.search(r'MDL-\d+', message)  # 使用正则表达式来匹配 "MDL-" 格式的 issue key
    if match:
        return match.group()  # 返回匹配到的 issue key
    else:
        return None



filtered_messages.loc[:,'issuekey'] = filtered_messages_cpy['message'].apply(extract_issue_key)



df_commits_filter = filtered_messages[filtered_messages['created'] >= '2014-11-9']



df_commits_filter2 = df_commits_filter[df_commits_filter['created'] - df_commits_filter['committed'] <= timedelta(days=1)]




df_commits_filter2 = df_commits_filter2.drop_duplicates(subset=['issuekey','total','changefiles','files'])




def calculate_and_remove_rows(df):
    # 找出issuekey重复的行
    duplicate_issuekeys = df[df.duplicated(subset=['issuekey'], keep=False)]

    rows_to_remove = []
    for key, group in duplicate_issuekeys.groupby('issuekey'):
        # 按committed列排序
        group = group.sort_values(by='committed')
        
        # 计算相邻committed时间的时间间隔
        previous_commit = None
        for i in range(len(group)):
            if i == 0:
                previous_commit = group.iloc[i]['committed']
                continue
            
            current_commit = group.iloc[i]['committed']
            time_diff = (current_commit - previous_commit).days
            
            # 检查时间间隔是否超过7天，若超过则标记需要删除的行
            if time_diff > 7:
                rows_to_remove.extend(group.iloc[i:].index.tolist())
                break
            
            previous_commit = current_commit

    # 删除需要移除的行
    df_cleaned = df.drop(rows_to_remove)
    return df_cleaned




df_commits_filter2 = calculate_and_remove_rows(df_commits_filter2)

df_commits_filter2 = df_commits_filter2.drop_duplicates(subset=['issuekey','total','changefiles','files'])



df_commits_filter2.shape[0]



df_stable2 = df_stable[df_stable['issuekey'].isin(df_commits_filter2['issuekey'])]




merged_df = pd.merge(df_commits_filter2, df_stable, on='issuekey', how='inner')




merged_df.shape[0]

filtered_df3 = df_stable[df_stable.issuekey.isin(merged_df.issuekey)]

filtered_df3.shape[0]



filtered_messages2 = filtered_messages.copy()

filtered_messages3 = filtered_messages2[filtered_messages2.issuekey.isin(merged_df.issuekey)]



filtered_df4 = filtered_df3.copy()
filtered_df4.replace(np.nan, None, inplace=True)



conn = connect_to_mysql('moodle_bug')
cursor = conn.cursor()

# 将 DataFrame 中的数据插入到 MySQL 数据库中
for index, row in filtered_df4.iterrows():
    sql = "INSERT INTO issuesbugs_used(issueid, issueself, issuekey, fixversions, summary, project, issuetype, issuestatus, priority, versions, issuelinks, subtasks, resolution, assignee, labels, components, creator, reporter, timespent, created, updated, resolutiondate, description, comments, watchcount) VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s)"
    cursor.execute(sql, tuple(row))

# 提交事务
conn.commit()

cursor.close()
conn.close()



conn = connect_to_mysql('moodle_bug')
cursor = conn.cursor()

# 将 DataFrame 中的数据插入到 MySQL 数据库中
for index, row in filtered_messages3.iterrows():
    sql = "INSERT INTO github_commits_used(sha, oid, author, created, committer, committed, message, commentcount, verified, reason, total, additions, deletions, changefiles, files, issuekey) VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor.execute(sql, tuple(row))

# 提交事务
conn.commit()

cursor.close()
conn.close()



merged_df1 = merged_df.copy()
merged_df1.replace(np.nan, None, inplace=True)




conn = connect_to_mysql('moodle_bug')
cursor = conn.cursor()


# 将 DataFrame 中的数据插入到 MySQL 数据库中
for index, row in merged_df1.iterrows():
    sql = "INSERT INTO issuesbugsandcommit(sha, oid, commitauthor, commitcreated, commitcommitter, committed, commitmessage, commentcount, verified, reason, total, additions, deletions, changefiles, files, issuekey, issueid, issueself, fixversions, summary, project, issuetype, issuestatus, priority, versions, issuelinks, subtasks, resolution, assignee, labels, components, creator, reporter, timespent, created, updated, resolutiondate, description, comments, watchcount) VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor.execute(sql, tuple(row))

# 提交事务
conn.commit()

cursor.close()
conn.close()

