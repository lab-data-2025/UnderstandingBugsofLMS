#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import openpyxl
import mysql.connector
import pandas as pd
import numpy as np
from math import log2
from datetime import timedelta


# In[2]:


def connect_to_mysql(database):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database=database
    )
    return conn

# 从MySQL中检索数据
def fetch_data_from_mysql(conn, table_name, *columns):
    columns_str = ', '.join(columns)
    query = "SELECT issueid, issuekey,{} FROM {}".format(columns_str, table_name)
    df = pd.read_sql(query, conn)
    return df


# In[3]:


conn = connect_to_mysql('moodle_bug')
df_bugs = fetch_data_from_mysql(conn,'issuesbugs_used', 'created', 'resolutiondate', 'comments')
conn.close()
print('数据条数：', df_bugs.shape[0])


# In[4]:


filtered_df = df_bugs[df_bugs['created'] >= '2014-11-9']


# In[5]:


conn = connect_to_mysql('moodle_bug')
df_commits = fetch_data_from_mysql(conn,'issuesbugsandcommit','sha','committed','total','changefiles','files','created')
conn.close()
# print('数据条数：', df_commits.shape[0])


# In[6]:


df_commits = df_commits[df_commits['created'] >= '2014-11-9']
# print('数据条数：', df_commits.shape[0])


# In[7]:


filtered_df_commits = df_commits[df_commits['created'] - df_commits['committed'] <= timedelta(days=1)]


# In[8]:


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


# In[9]:


df_cleaned = calculate_and_remove_rows(filtered_df_commits)
# print(df_cleaned.shape[0])


# In[10]:


df_cleaned = df_cleaned.drop_duplicates(subset=['issuekey','total','changefiles','files'])
# print(df_cleaned.shape[0])


# In[11]:


def calculate_metrics(df, df2):
    # 计算OT列
    df['OT'] = (df['resolutiondate'] - df['created']).dt.total_seconds()
    df['OT'] = df['OT'].apply(lambda x: '{:02}:{:02}:{:02}'.format(int(x // 3600), int((x % 3600) // 60), int(x % 60)))

    # 计算LOCM列和NOFM列
    issuekey_totals = df2.groupby('issuekey')['total'].sum().reset_index()
    issuekey_changefiles = df2.groupby('issuekey')['changefiles'].sum().reset_index()

    # 将 LOCM 和 NOFM 列合并到 df 中
    df = df.merge(issuekey_totals, how='left', left_on='issuekey', right_on='issuekey', suffixes=('', '_df2'))
    df = df.merge(issuekey_changefiles, how='left', left_on='issuekey', right_on='issuekey', suffixes=('', '_df2'))

    return df


# In[12]:


df_processed = calculate_metrics(filtered_df, df_cleaned)


# In[13]:


df_processed.rename(columns={'total': 'LOCM', 'changefiles': 'NOFM'}, inplace=True)


# In[14]:


def calculate_noc_nodp(comments_json):
    comments_data = json.loads(comments_json)
    noc = comments_data.get("total", 0)
    
    distinct_display_names = {comment["author"] for comment in comments_data["comments"]}
    nodp = len(distinct_display_names)
    return noc, nodp


# In[15]:


# 应用函数计算每行的 NOC 和 NODP
df_processed[['NOC', 'NODP']] = df_processed['comments'].apply(lambda x: pd.Series(calculate_noc_nodp(x)))


# In[16]:


# 解析文件列表
def parse_files(files):
    return [item['filename'] for item in json.loads(files)]

# 计算熵的函数
def compute_entropy(df, issuekey, commit_date):
    # 获取当前 issuekey 的修改文件
    current_files = set(df[df['issuekey'] == issuekey]['filenames'].sum())
    
    # 找到在当前 issuekey 的 commit_date 前 60 天的其他 issuekey 的文件
    start_date = commit_date - timedelta(days=60)
    relevant_df = df[(df['committed'] <= commit_date) & (df['committed'] >= start_date) & (df['issuekey'] != issuekey)]
    
    # 计算每个文件在其他文件集中的出现次数
    file_counts = {}
    for file in current_files:
        file_counts[file] = 0

    for files in relevant_df['filenames']:
        unique_files = set(files)
        for file in unique_files:
            if file in file_counts:
                file_counts[file] += 1
            
    # 计算熵 H(n)
    total_files = sum(file_counts.values())
    if total_files == 0 or len(current_files) == 0:
        return 0

    entropy = 0
    for file in current_files:
        pi = file_counts.get(file, 0) / total_files
        if pi > 0:
            entropy -= pi * log2(pi)
            
    # 归一化熵
    normalized_entropy = 0
    n = len(current_files)
    if n > 1:
        normalized_entropy = entropy / log2(n)
    
    return normalized_entropy

# 针对 df1 的每个 issuekey 计算归一化熵并保存到 df1 中
def calculate_and_save_entropy(row, df):
    issuekey = row['issuekey']
    committed = df[df['issuekey'] == issuekey]['committed'].min()
    entropy = compute_entropy(df, issuekey, committed)
    return entropy


# In[17]:


df_processed = df_processed[df_processed['issuekey'].isin(df_cleaned['issuekey'])]


# In[19]:


df_cleaned['filenames'] = df_cleaned['files'].apply(parse_files)
df_processed['Entropy']  = df_processed.apply(calculate_and_save_entropy, axis=1, df=df_cleaned)


# In[20]:


df_cluster = pd.read_excel('Moodle_BugCluster_Type16.xlsx')
# print(df_cluster.shape[0])


# In[21]:


# 输出未根据代码行删除前的结果

category_counts = df_cluster['ClusterConvers'].value_counts()

# 计算每个类别的百分比
category_percentage = df_cluster['ClusterConvers'].value_counts(normalize=True) * 100

# 将结果放入一个新的 DataFrame 中
result = pd.DataFrame({
    'Count': category_counts,
    'Percentage': category_percentage
})
result =result.reset_index()
result.columns = ['Cluster_label', 'Count', 'Percentage']
print(result)

result.to_excel('F:/Download/result/moodle_category_result.xlsx', index=False)


# In[22]:


df_cluster_select = df_cluster[['issueid', 'ClusterConvers']]


# In[23]:


merged_df = pd.merge(df_processed, df_cluster_select, on='issueid', how='left')


# In[24]:


df_filtered = merged_df[(merged_df['LOCM'] <= 2000) & (merged_df['NOFM'] <= 100)]


# In[25]:


df_filtered = merged_df[(merged_df['LOCM'] <= 10000) & (merged_df['NOFM'] <= 100)]
# print(df_filtered.shape[0])


# In[26]:


df_filtered['OT'] = pd.to_timedelta(df_filtered['OT']).dt.total_seconds()

# 计算每个分组的中位数和平均数
grouped_stats = df_filtered[[ 'OT', 'LOCM', 'NOFM', 'NOC', 'NODP', 'Entropy', 'ClusterConvers']].groupby('ClusterConvers').agg(['median', 'mean'])

# 计算整个DataFrame的中位数和平均数
overall_stats = df_filtered[[ 'OT', 'LOCM', 'NOFM', 'NOC', 'NODP', 'Entropy']].agg(['median', 'mean'])


# In[27]:


grouped_stats['OT', 'median'] = pd.to_timedelta(grouped_stats['OT', 'median'], unit='s')
grouped_stats['OT', 'mean'] = pd.to_timedelta(grouped_stats['OT', 'mean'], unit='s')
overall_stats.loc['median', 'OT'] = pd.to_timedelta(overall_stats.loc['median', 'OT'], unit='s')
overall_stats.loc['mean', 'OT'] = pd.to_timedelta(overall_stats.loc['mean', 'OT'], unit='s')


# In[28]:


category_counts = df_filtered['ClusterConvers'].value_counts()

# 计算每个类别的百分比
category_percentage = df_filtered['ClusterConvers'].value_counts(normalize=True) * 100

# 将结果放入一个新的 DataFrame 中
result = pd.DataFrame({
    'Count': category_counts,
    'Percentage': category_percentage
})
result =result.reset_index()
result.columns = ['Cluster_label', 'Count', 'Percentage']


# In[40]:


with pd.ExcelWriter('Moodle_output_Indicators.xlsx') as writer:
    df_filtered.to_excel(writer, sheet_name='Indicators', index=False)
    result.to_excel(writer, sheet_name='resultCluster', index=False)
    grouped_stats.to_excel(writer, sheet_name='Grouped Stats')
    overall_stats.to_excel(writer, sheet_name='Overall Stats')

