#!/usr/bin/env python
# coding: utf-8

# In[9]:


import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score


# In[2]:


df_ada=pd.read_csv('Moodle_embedding_dimensions256.csv')


# In[3]:


df_ada_select = df_ada[['issueid', 'description']]


# In[4]:


df_description = pd.read_excel('Moodle_OpenAI_BugCluter58_dim256.xlsx')
# print(df_description.shape[0])


# In[5]:


replace_dict = {18:1, 21:1, 38:1, 41:1, 44:1, 49:1, 50:1, 51:1, 1:2, 7:3, 30:3, 6:4, 27:4, 32:4, 57:4, 5:5, 12:5, 16:5, 20:5, 42:5, 53:5, 2:6, 15:6, 22:6, 37:6, 54:6, 55:6, 8:7, 0:8, 4:8, 13:8, 31:8, 47:9, 14:10, 45:10, 9:11, 23:11, 33:11, 52:11, 3:12, 10:12, 19:12, 24:12, 28:12, 29:12, 34:12, 35:12, 36:12, 39:12, 40:12, 43:12, 46:12, 48:12, 56:13, 17:14, 11:15, 25:16, 26:16}

df_description['ClusterConvers'] = df_description['Cluster'].replace(replace_dict)


# In[6]:


merged_df_des = pd.merge(df_description, df_ada_select, on='issueid', how='left')


# In[7]:


last_column = merged_df_des.columns[-1]  # 获取最后一列的列名
other_columns = list(merged_df_des.columns[:-1])  # 除去最后一列的所有列
other_columns.insert(3, last_column)  # 2是索引，第三列的位置
merged_df_des = merged_df_des[other_columns]


# In[8]:


df_description.to_excel('Moodle_BugCluster_Type16.xlsx', index=False)


# In[9]:


merged_df_des.to_csv('Moodle_BugCluster_Type16.csv', index=False)

