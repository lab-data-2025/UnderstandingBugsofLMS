#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score


# In[2]:


df_ada=pd.read_csv('Sakai_embedding_dimensions256.csv')


# In[3]:


df_ada_select = df_ada[['issueid', 'description']]


# In[4]:


df_description = pd.read_excel('Sakai_OpenAI_BugCluter52_dim256.xlsx')
# print(df_description.shape[0])


# In[5]:


replace_dict = {3:1, 16:1, 23:1, 29:1, 39:1, 42:1, 7:2, 30:3, 10:4, 20:4, 27:4, 41:4, 49:4, 5:5, 33:5, 45:5, 17:6, 31:6, 32:6, 4:7, 6:7, 12:7, 26:7, 47:7, 2:8, 8:8, 9:8, 22:8, 24:8, 44:8, 48:8, 1:9, 38:10, 14:11, 34:11, 46:11, 0:12, 13:12, 19:12, 35:12, 36:12, 37:12, 40:12, 51:12, 15:13, 21:14, 25:14, 28:14, 43:14, 50:14, 11:15, 18:16}
df_description['ClusterConvers'] = df_description['Cluster'].replace(replace_dict)


# In[7]:


merged_df_des = pd.merge(df_description, df_ada_select, on='issueid', how='left')


# In[8]:


last_column = merged_df_des.columns[-1]  # 获取最后一列的列名
other_columns = list(merged_df_des.columns[:-1])  # 除去最后一列的所有列
other_columns.insert(3, last_column)  # 2是索引，第三列的位置
merged_df_des = merged_df_des[other_columns]


# In[10]:


df_description.to_excel('Sakai_BugCluster_Type16.xlsx', index=False)


# In[11]:


merged_df_des.to_csv('Sakai_BugCluster_Type16.csv', index=False)

