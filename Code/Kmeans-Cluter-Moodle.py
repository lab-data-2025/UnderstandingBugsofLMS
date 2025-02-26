#!/usr/bin/env python
# coding: utf-8

# In[6]:


import os
from dotenv import load_dotenv
os.environ["OMP_NUM_THREADS"] = '8'


# In[7]:


import openai
from openai import OpenAI
import openpyxl
import json
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
import time
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.manifold import TSNE
from sklearn.metrics import davies_bouldin_score


# In[5]:


# Your OpenAI api
load_dotenv()
openAI_api = os.getenv("OPENAI_API_KEY")
client = OpenAI(
    api_key=openAI_api
)


# In[8]:


df=pd.read_csv('Moodle_embedding_dimensions256.csv')


# In[6]:


df.shape[0]


# In[9]:


df['ada_embedding'] = df.ada_embedding.apply(json.loads).apply(np.array)
matrix = np.vstack(df.ada_embedding.values)


# In[11]:


db_scores = []
# 使用DBI选择最佳聚类数
def find_best_k(data, max_k=60):
    k_values = range(3, max_k + 1)
    
    for k in k_values:
        kmeans = KMeans(n_clusters=k, init='k-means++', random_state=42, n_init=10)
        y = kmeans.fit(data)
        labels = kmeans.labels_
        db_scores.append(davies_bouldin_score(data, labels))
    
    # 绘制Davies-Bouldin指数图
    plt.figure(figsize=(10, 5))
    plt.plot(k_values, db_scores, marker='o')
    plt.xlabel('Number of Clusters (k)')
    plt.ylabel('Davies-Bouldin Index')
    plt.xticks(k_values[::2])
    plt.grid(True)
#     plt.savefig('DBI-Moodle.pdf', format='pdf')  # 或者使用 .svg 文件格式
    plt.show()
    
    # 返回最佳 k 值
    best_k = k_values[np.argmin(db_scores)]
    return best_k


# In[12]:


# 找到最佳的 k 值
reduced_embeddings = TSNE(n_components=2, random_state=45).fit_transform(matrix)
normalized_matrix = normalize(reduced_embeddings)
best_k = find_best_k(normalized_matrix)


# In[12]:


k_values = range(3, 60 + 1)
# 绘制Davies-Bouldin指数图
plt.figure(figsize=(10, 5))
plt.plot(k_values, db_scores, marker='o')
# plt.plot(k_values, db_scores, marker='o', linestyle='-', color='black')  # 线条设置
plt.xlabel('Number of Clusters (k)', fontsize=14)
plt.ylabel('Davies-Bouldin Index', fontsize=14)
plt.xticks(k_values[::2], fontsize=12)
plt.yticks(fontsize=12)  # 增大y轴刻度的字号
ax = plt.gca()  # 获取当前坐标维
ax.spines['top'].set_visible(False)  # 隐藏上边框
ax.spines['right'].set_visible(False)  # 隐藏右边框
# ax.spines['left'].set_position(('outward', 10))  # 向外移动左边框（可选）
# ax.spines['bottom'].set_position(('outward', 10))  # 向外移动下边框（可选）
# # 禁用网格的竖线，只保留横线
ax.yaxis.grid(True)  # 仅开启横线网格
ax.xaxis.grid(False)  # 禁用竖线网格
# plt.grid(True)  # 仅给出横线网格
plt.savefig('DBI-Moodle.pdf', format='pdf', bbox_inches='tight')  # 或者使用 .svg 文件格式
plt.show()


# In[15]:


best_k


# In[18]:


# final k-mean clustering
km_model = KMeans(n_clusters = best_k, init = 'k-means++', random_state = 42, n_init = 10)
y = km_model.fit_predict(matrix)
df['Cluster']=y


# In[19]:


label_counts = df['Cluster'].value_counts()
print(label_counts)
label_counts_df = label_counts.reset_index()
label_counts_df.columns = ['Cluster_label', 'Count']


# In[21]:


# 将嵌入和话题编号进行配对
filtered_text = df['clean_text'].tolist()
topics = df['Cluster'].tolist()
topic_texts_dict = {}
for text, topic in zip(filtered_text, topics):
    if topic not in topic_texts_dict:
        topic_texts_dict[topic] = []
    topic_texts_dict[topic].append(text)


# In[23]:


def generate_cluster_label(texts):
    prompt = "Here are summaries of bugs belonging to the same category. Please write an appropriate category label for these summaries.\n\nSummaries: " + " ".join(texts)
    completion = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a software engineer familiar with bugs in the LMS system's issue tracker. You are helping me extract a category label for bugs of the same type from their summaries."},
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content.strip()


# In[24]:


# 对每个话题生成标签
topic_labels = {}
for topic, topic_texts in topic_texts_dict.items():
    label = generate_cluster_label(topic_texts)
    topic_labels[topic] = label


# In[25]:


topic_labels_df = pd.DataFrame(list(topic_labels.items()), columns=['Id', 'Topic'])


# In[26]:


df2=df[['issueid','issuekey','summary','created','clean_text','Cluster']]
df2 = df2.astype(str)
df2 = df2.fillna('')
with pd.ExcelWriter('Moodle_OpenAI_BugCluter58_dim256.xlsx') as writer:
    df2.to_excel(writer, sheet_name='ClusterResult', index=False)
    label_counts_df.to_excel(writer, sheet_name='LabelCounts58', index=False)
    topic_labels_df.to_excel(writer, sheet_name='LabelTopic58', index=False)

