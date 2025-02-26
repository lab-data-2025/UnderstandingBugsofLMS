#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import mysql.connector
import pandas as pd
import numpy as np
from math import log2
from datetime import timedelta


# In[4]:


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


# In[5]:


conn = connect_to_mysql('moodle_bug')
df_bugs = fetch_data_from_mysql(conn,'issuesbugs_used', 'created', 'resolutiondate', 'comments')
conn.close()
# print('数据条数：', df_bugs.shape[0])


# In[7]:


filtered_df = df_bugs[df_bugs['created'] >= '2014-11-9']


# In[9]:


conn = connect_to_mysql('moodle_bug')
df_commits = fetch_data_from_mysql(conn,'issuesbugsandcommit','sha','committed','total','changefiles','files','created')
conn.close()
# print('数据条数：', df_commits.shape[0])


# In[10]:


df_commits = df_commits[df_commits['created'] >= '2014-11-9']
# print('数据条数：', df_commits.shape[0])
filtered_df_commits = df_commits[df_commits['created'] - df_commits['committed'] <= timedelta(days=1)]


# In[14]:


# 有多个commit时
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


# In[15]:


df_cleaned = calculate_and_remove_rows(filtered_df_commits)
df_cleaned = df_cleaned.drop_duplicates(subset=['issuekey','total','changefiles','files'])
# print(df_cleaned.shape[0])


# In[17]:


df_module = pd.read_excel('Moodle_Module and Files_Correspondence.xlsx')
# print(df_module.shape[0])


# In[18]:


def find_module_by_path(file_path, df):
    # 查找对应模块
    for index, row in df.iterrows():
        if row['content'] in file_path:
            return row['module']
    return "Runtime Environment"


# In[19]:


# 解析文件列表
def parse_files(files):
    return [item['filename'] for item in json.loads(files)]


# 针对 df1 的每个 issuekey 计算其属于哪些模块
def calculate_and_save_module(row, df):
    issuekey = row['issuekey']
    repair_filesname = set(df[df['issuekey'] == issuekey]['filenames'].sum())
    
    row['repair_filesname'] = list(repair_filesname)
    # 计算每个bug在不同模块的修改文件数
    module_counts = {}
    count = 0
    for filename in repair_filesname:
        module = find_module_by_path(filename, df_module)
        if(module == 'notfound'):
            count += 1
            print(filename + 'notfound')
        if module not in module_counts:
                module_counts[module] = 0
        module_counts[module] += 1
    if count != 0:
        print(count)
    return module_counts


# In[20]:


# 除去没有修复commit的bug
filtered_df = filtered_df[filtered_df['issuekey'].isin(df_cleaned['issuekey'])]
df_cleaned['filenames'] = df_cleaned['files'].apply(parse_files)
filtered_df['module']  = filtered_df.apply(calculate_and_save_module, axis=1, df=df_cleaned)


# In[23]:


df_cluster = pd.read_csv('Moodle_BugCluster_Type16.csv')
df_cluster_select = df_cluster[['issueid', 'ClusterConvers']]
merged_df = pd.merge(filtered_df, df_cluster_select, on='issueid', how='left')
merged_df_save = merged_df[['issueid','issuekey','module','ClusterConvers']]


# In[27]:


# Step 1: 处理模块数据，展开每个字典并标记存在性
module_expanded = pd.DataFrame(merged_df['module'].apply(lambda x: {k: 1 for k in x.keys()}).tolist()).fillna(0)

# Step 2: 计算每种类型出现的总次数/所占比重
module_counts = module_expanded.sum().rename("TotalCount")
# print(module_counts)

total_counts= module_counts.sum()
module_ratios = module_counts / total_counts
# print("\n每种模块类型的比例：")
# print(module_ratios)


# In[28]:


result_loc = df_module.groupby('module')['code'].sum().reset_index()
final_result_2 = (module_counts * 1000) / result_loc.set_index('module')['code']
print(final_result_2)


# In[29]:


with pd.ExcelWriter('Moodle_Bug_on_Component.xlsx') as writer:
    merged_df_save.to_excel(writer, sheet_name='Module', index=False)
    module_counts.to_excel(writer, sheet_name='BugNumsofModule', index=False)
    module_ratios.to_excel(writer, sheet_name='BugRatiosofModule')

