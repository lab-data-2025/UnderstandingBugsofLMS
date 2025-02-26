#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import openai
from openai import OpenAI
import mysql.connector
import pandas as pd
import numpy as np
from dotenv import load_dotenv


# In[2]:


import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem import SnowballStemmer


# In[3]:


# Your OpenAI api
load_dotenv()
openAI_api = os.getenv("OPENAI_API_KEY")
client = OpenAI(
    api_key=openAI_api
)


# In[3]:


def connect_to_mysql(database):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database=database
    )
    return conn

# 从MySQL中检索数据
def fetch_data_from_mysql(conn, column1, column2):
    query = "SELECT issueid, issuekey, {}, {}, created FROM issuesbugs_used".format(column1,column2)
    df = pd.read_sql(query, conn)
    return df


# In[4]:


conn = connect_to_mysql('sakai_bug')
df = fetch_data_from_mysql(conn, 'summary', 'description')
conn.close()
print('数据条数：', df.shape[0])


# In[5]:


df_stable = df[df['created'] >= '2014-12-29']


# In[6]:


df_stable.shape[0]


# In[6]:


new_stop_words = {'label', 'labels','sort', 'portal', 'index', 'bug', 'role', 'content','error', 'remove','add', 'site', 'group', 'groups'}


# In[7]:


# 数据清洗
def preprocess_text(text):
    # 转换为小写
    text = text.lower()
    #去除非文本内容：去除URL和HTML标签
    text = re.sub(r'http\S+|www\S+|<.*?>','',text)
    #去除数字
    text = re.sub(r'\d+','',text)
    # 去除特殊字符和标点符号
    text = re.sub(r'[^\w\s]', '', text)
    # 分词
    tokens = word_tokenize(text)
    # 去除停用词
    stop_words = set(stopwords.words('english'))
    stop_words.update(new_stop_words)
    tokens = [word for word in tokens if word not in stop_words]
    stemmer = SnowballStemmer(language='english')
    tokens = [stemmer.stem(word) for word in tokens]
    # 连接为字符串
    cleaned_text = ' '.join(tokens)

    return cleaned_text

# 数据预处理
def preprocess_data(df, column):
    # 进行文本清洗、标记化等预处理操作
    # 这里的示例假设你已经有了文本预处理函数
    # preprocess_text(text) 对每一行文本进行预处理
    df[column] = df[column].fillna('')
    df['clean_text'] = df[column].apply(preprocess_text)
    return df


# In[8]:


df_stable = preprocess_data(df_stable, 'summary')
df_stable = df_stable.astype(str)


# In[17]:


# 数据清洗
def preprocess_text_description(text):
    # 转换为小写
    text = text.lower()
    #去除非文本内容：去除URL和HTML标签
    text = re.sub(r'http\S+|www\S+|<.*?>','',text)
    #去除数字
    text = re.sub(r'\d+','',text)

    return text

# 数据预处理
def preprocess_data_des(df, column):
    # 进行文本清洗、标记化等预处理操作
    # 这里的示例假设你已经有了文本预处理函数
    # preprocess_text(text) 对每一行文本进行预处理
    df[column] = df[column].fillna('')
    df['clean_text_des'] = df[column].apply(preprocess_text_description)
    return df


# In[19]:


summary_gpt_list = []


# In[20]:


def get_summary_from_gpt(text):
    prompt = "Summarize the main content described below using no less than 5 and no more than 20 words.\n\nDescription：" + text[:100]
    completion = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a software engineer familiar with the bug descriptions in the LMS system's issue tracker. Please extract a concise summary from the bug description for me."},
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content.strip()

def process_row(row):
    clean_text_words = row['clean_text'].split()
    if len(clean_text_words) < 3:
        description = row['clean_text_des']
        new_summary = preprocess_text(get_summary_from_gpt(description))
        # print(summary_gpt)
        summary_gpt_list.append(new_summary)
        row['clean_text'] = new_summary
#         print(row['clean_text'])
    return row


# In[ ]:


df_stable = preprocess_data_des(df_stable, 'description')


# In[21]:


df_stable = df_stable.apply(process_row, axis=1)


# In[29]:


def get_embedding(text, model="text-embedding-3-large"):
    text = text.replace("\n", " ")

    return client.embeddings.create(input=[text], model=model, dimensions=256).data[0].embedding


# In[30]:


df_stable['ada_embedding'] = df_stable.clean_text.apply(lambda x: get_embedding(x, model='text-embedding-3-large'))


# In[31]:


df_stable.to_csv('Sakai_embedding_dimensions256.csv', index=False)

