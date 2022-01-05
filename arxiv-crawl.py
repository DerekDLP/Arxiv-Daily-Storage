#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import urllib.request as libreq
from xml.dom.minidom import parseString
import pandas as pd
import datetime
import requests
import json
import os
import yaml
from codecs import open
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
import time
import random

# paperWithCode API
base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"

def get_authors(authors, first_author=False):
    output = str()
    if first_author == False:
        output = ", ".join(str(author) for author in authors)
    else:
        output = authors[0]
    return output

def get_categories(categories):
    return ", ".join(str(category) for category in categories).replace('\n', ' ')

def sort_papers(papers):
    output = dict()
    keys = list(papers.keys())
    keys.sort(reverse=False)
    for key in keys:
        output[key] = papers[key]
    return output

def get_yaml_data(yaml_file: str):
    with open(yaml_file, encoding='utf-8') as fs:
        data = yaml.load(fs, Loader=Loader)
    return data

def set_subtopic_historyCount(topic, subtopic, count, yaml_file):
    with open(yaml_file, encoding='utf-8') as fs:
        data = yaml.safe_load(fs)
        data[topic][subtopic]["historyCount"] = count
    with open(yaml_file, 'w', encoding='utf-8') as fs:
        yaml.safe_dump(data, fs, default_flow_style=False)

def getResult(search_query='all:fake+news+OR+all:rumour', start=0, history_results=1, sortBy='submittedDate', sortOrder='descending'):
    url = 'http://export.arxiv.org/api/query?search_query={}&start={}&max_results={}&sortBy={}&sortOrder={}'.format(
        search_query, 0, 1, sortBy, sortOrder
    )
    data = libreq.urlopen(url)
    xml_data = data.read()
    DOMTree = parseString(xml_data)
    collection = DOMTree.documentElement
    total = int(collection.getElementsByTagName("opensearch:totalResults")[0].childNodes[0].data)
    diff = total - history_results
    if diff <= 0:
        return [], False, diff
    if diff > 10000:
        diff = 10000
    url = 'http://export.arxiv.org/api/query?search_query={}&start={}&max_results={}&sortBy={}&sortOrder={}'.format(
        search_query, start, diff, sortBy, sortOrder
    )
    data = libreq.urlopen(url)
    xml_data = data.read()
    DOMTree = parseString(xml_data)
    collection = DOMTree.documentElement
    entrys = collection.getElementsByTagName("entry")
    results = []
    for entry in entrys:
        paper_url = entry.getElementsByTagName('id')[0].childNodes[0].data
        paper_updated_time = entry.getElementsByTagName('updated')[0].childNodes[0].data
        paper_published_time = entry.getElementsByTagName('published')[0].childNodes[0].data
        paper_title = entry.getElementsByTagName('title')[0].childNodes[0].data.replace('\n', ' ')
        paper_summary = entry.getElementsByTagName('summary')[0].childNodes[0].data.replace('\n', ' ')
        authors = entry.getElementsByTagName('author')
        paper_authors = []
        for author in authors:
            paper_authors.append(author.getElementsByTagName('name')[0].childNodes[0].data)
        paper_journal = 'null'
        if len(entry.getElementsByTagName('arxiv:journal_ref')) > 0:
            paper_journal = entry.getElementsByTagName('arxiv:journal_ref')[0].childNodes[0].data.replace('\n', ' ')
        paper_primary_category = entry.getElementsByTagName('arxiv:primary_category')[0].attributes["term"].nodeValue
        categories = entry.getElementsByTagName('category')
        paper_categories = []
        for category in categories:
            paper_categories.append(category.attributes["term"].nodeValue)
        results.append({
            'paper_id': paper_url.split('arxiv.org/abs/')[-1],
            'paper_url': paper_url,
            'paper_pdf_url': paper_url.replace('/abs/', '/pdf/'),
            'paper_updated_time': paper_updated_time.replace('T', ' ').replace('Z', ''),
            'paper_published_time': paper_published_time.replace('T', ' ').replace('Z', ''),
            'paper_title': paper_title,
            'paper_summary': paper_summary,
            'paper_authors': paper_authors,
            'paper_journal': paper_journal,
            'paper_primary_category': paper_primary_category,
            'paper_categories': paper_categories,
        })
    return results, True, total

def get_daily_papers(topic: str, subtopic: str, query: str = "fake news", historyTotal=0):
    """
    @param topic: str
    @param query: str
    @return paper_with_code: dict
    """
    # output
    content = dict()
    excel_data = list()
    results, flag, diff = getResult(search_query=query, history_results=historyTotal)
    if flag:
        for result in results:
            paper_url      = result['paper_url']
            paper_id       = result['paper_id']
            update_time = result['paper_updated_time']
            publish_time = result['paper_published_time']
            paper_title    = result['paper_title'].replace('\n', ' ')
            paper_authors  = get_authors(result['paper_authors'])
            paper_first_author = get_authors(result['paper_authors'], first_author=True)
            paper_summary = result['paper_summary'].replace("\n"," ")
            paper_journal_ref = result['paper_journal'].replace("\n"," ")
            # primary_category = result['paper_primary_category']
            paper_categories = get_categories(result['paper_categories'])
            
            # paper_links = result.links
            paper_pdf_url = result['paper_pdf_url']
            code_url       = base_url + paper_id # paperWithCode

            # eg: 2108.09112v1 -> 2108.09112
            ver_pos = paper_id.find('v')
            if ver_pos == -1:
                paper_key = paper_id
            else:
                paper_key = paper_id[0: ver_pos]

            try:
                r = requests.get(code_url).json()
                # source code link
                if "official" in r and r["official"]:
                    repo_url = r["official"]["url"]
                    repo_url = '**[link]({})**'.format(repo_url)
                else:
                    repo_url = 'null'
                if 'https://github.com' in paper_summary:
                    code = paper_summary.split('https://github.com')[-1].replace('\n', '').replace(' ', '')
                    if code.endswith("."):
                        code = code[:-1]
                        if repo_url == 'null':
                            repo_url = '**[link]({})**'.format('https://github.com' + code[:-1])
                if paper_journal_ref:
                    content[paper_key] = f"|**{publish_time}**|**{update_time}**|**{paper_title}**|{paper_first_author} et.al.({len(result['paper_authors'])})|[{paper_id}]({paper_url})|[gotoRead]({paper_pdf_url})|{repo_url}|{paper_categories}|{paper_journal_ref}|\n"
                    excel_data.append((
                        paper_id,
                        publish_time,
                        update_time,
                        paper_title,
                        paper_authors,
                        paper_summary,
                        paper_journal_ref,
                        paper_categories,
                        paper_url,
                        paper_pdf_url,
                        repo_url.replace('**[link](', '').replace(')**', ''),
                        topic,
                        subtopic
                    ))
                else:
                    content[paper_key] = f"|**{publish_time}**|**{update_time}**|**{paper_title}**|{paper_first_author} et.al.({len(result['paper_authors'])})|[{paper_id}]({paper_url})|[gotoRead]({paper_pdf_url})|{repo_url}|{paper_categories}|null|\n"
                    excel_data.append((
                        paper_id,
                        publish_time,
                        update_time,
                        paper_title,
                        paper_authors,
                        paper_summary,
                        'null',
                        paper_categories,
                        paper_url,
                        paper_pdf_url,
                        repo_url.replace('**[link](', '').replace(')**', ''),
                        topic,
                        subtopic
                    ))
                time.sleep(random.random()*2)

            except Exception as e:
                print(f"exception: {e} with id: {paper_key}")

        return content, flag, excel_data, diff
    return content, flag, excel_data, diff


def data_to_md(cur_date: str, data: dict, topic: str, subtopic: str):
    """
    @param md_filename: str
    @return None
    """
    if not data:
        return
    suffix = 0
    cur = 1000
    # sort papers by date
    day_content = sort_papers(data)
    for _, v in day_content.items():
        if cur == 1000:
            suffix += 1
            md_filename = "mds/[{}]{}-{}({}).md".format(topic, subtopic, cur_date, suffix)
            cur = 0
            f = open(md_filename, "w+", encoding='utf-8')
            f.write("## [" + topic + "]" + subtopic + " \n\n")
            # the head of each part
            f.write(f"### {subtopic}\n\n")

            f.write("| submit | update | title | author | abs | PDF | code | cates | journal |\n" +
                "|---|---|---|---|---|---|---|---|---|\n")

        if v is not None:
            # print(type(v), v)
            f.write(v)
            cur += 1

    print("add md file finished（{}）".format(len(data)))

def data_to_excel(cur_date: str, data: dict, topic: str, subtopic: str):
    """
    @param excel_filename: str
    @return None
    """
    if not data:
        return
    excel_filename = "csvs/[{}]{}-{}.xlsx".format(topic, subtopic, cur_date)
    new_df = pd.DataFrame(data, columns=[
        'uuid',
        '提交日期',
        '更新日期',
        '标题',
        '作者',
        '摘要',
        '发表',
        '归类',
        'abs',
        'PDF',
        '代码',
        '主题',
        '子主题'
    ])
    new_df.to_excel(excel_filename, index=False)

    print("add excel file finished")


if __name__ == "__main__":
    yaml_path = os.path.join(".", "topic.yml")
    yaml_data = get_yaml_data(yaml_path)

    historyTotal = 0

    if not os.path.isdir('jsons'):
        os.mkdir('jsons')

    keywords = dict(yaml_data)
    for topic in keywords.keys():
        data_collector = dict()
        for subtopic, keywordInfo in dict(keywords[topic]).items():
            try:
                data, flag, excel_data, diff = get_daily_papers(
                    topic, subtopic, query=keywordInfo["query"], historyTotal=keywordInfo["historyCount"])
            except Exception as e:
                print(e)
                print(f'CANNOT get {subtopic} data from arxiv')
                data = None
                flag = False
#             # time.sleep(random.randint(2, 10))
            if flag:
                if not topic in data_collector.keys():
                    data_collector[topic] = {}

                if data:
                    cur_date = str(datetime.date.today())
                    data_collector[topic].update(data)
                    data_to_md(cur_date, data, topic, subtopic)
                    data_to_excel(cur_date, excel_data, topic, subtopic)
                set_subtopic_historyCount(topic, subtopic, diff, yaml_path)
                print(f"[{subtopic}] updated: {len(data)}")
            else:
                set_subtopic_historyCount(topic, subtopic, keywordInfo["historyCount"]+diff, yaml_path)
                print(f'[{subtopic}] data has no update({diff}) from arxiv')
        
        json_file = "jsons/{}-{}-arxiv-{}.json".format(topic, subtopic, str(datetime.date.today()))
        with open(json_file, 'w', encoding='utf-8') as a:
            a.write(json.dumps(data_collector))
