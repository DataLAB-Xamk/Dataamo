#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import re
import numpy as np

def extract_jurisdiction(x):
    if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict):
        return x[0]['jurisdiction']
    return np.nan

def get_english_text(texts):
    if isinstance(texts, list):
        texts = [text for text in texts if text.get('lang') == 'en']
        if texts:
            return texts[0]['text']
    return None

def list_length(list_value):
    return len(list_value)

def normalize_API_data(file):
    patentdata = pd.read_json(file)['data']
    df = pd.DataFrame(patentdata.values.tolist())
    df = pd.json_normalize(patentdata)
    return df

def cpc_table(file):
    df = normalize_API_data(file)
    exploded = df.explode('biblio.classifications_cpc.classifications')
    result = exploded[['lens_id', 'doc_key','biblio.classifications_cpc.classifications']].copy()
    result['cpc_classification'] = result['biblio.classifications_cpc.classifications'].apply(lambda x: x['symbol'] if type(x) == dict else None)
    result['class'] = result['cpc_classification'].str[0]
    data = {'class': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'Y'],
    'class_description': ['Human necessities', 'Performing operations; transporting', 'Chemistry; metallurgy', 'Textiles; paper', 'Fixed constructions', 'Mechanical engineering; lighting; heating; weapons; blasting engines or pumps', 'Physics', 'Electricity', 'General tagging of new technological developments; general tagging of cross-sectional technologies spanning over several sections of the IPC; technical subjects covered by former USPC cross-reference art collections [XRACs] and digests']}
    df2 = pd.DataFrame(data)
    result = result.merge(df2, on='class', how='left')
    del result['biblio.classifications_cpc.classifications']
    return result

def applicants_table(file):
    df = normalize_API_data(file)
    applicants = df[['lens_id','doc_key','biblio.parties.applicants']].copy()
    applicants = applicants.explode('biblio.parties.applicants')
    applicants_normalized = pd.json_normalize(applicants['biblio.parties.applicants'])
    applicants_normalized = applicants_normalized.reset_index(drop=True)
    applicants = applicants.reset_index(drop=True)
    applicants = pd.concat([applicants[['lens_id', 'doc_key']], applicants_normalized], axis=1)
    applicants['nimi'] = applicants['extracted_name.value']
    applicants.rename(columns={'extracted_name.value': 'extracted_name'}, inplace=True)
    return applicants

def patents_table(file):
    df = normalize_API_data (file)
    df['numInventors'] = df['biblio.parties.inventors'].fillna("").apply(list_length)
    df['numApplicants'] = df['biblio.parties.applicants'].fillna("").apply(list_length)
    df['invention_title'] = df['biblio.invention_title'].apply(lambda x: get_english_text(x))
    df = df[['lens_id', 'jurisdiction', 'date_published', 'doc_key',
       'publication_type', 'biblio.publication_reference.jurisdiction',
       'biblio.publication_reference.doc_number',
       'biblio.publication_reference.kind',
       'biblio.publication_reference.date',
       'biblio.application_reference.jurisdiction',
       'biblio.application_reference.doc_number',
       'biblio.application_reference.kind',
       'biblio.application_reference.date',
       'biblio.priority_claims.earliest_claim.date',
       'invention_title','description.text','description.lang','numApplicants', 
       'numInventors','biblio.references_cited.patent_count',
       'biblio.references_cited.npl_count']].copy()
    return df

def inventors_table(file):
    df = normalize_API_data(file)
    inventors = df[['lens_id', 'doc_key', 'biblio.parties.inventors']].copy()
    inventors['biblio.parties.inventors'].fillna("", inplace=True)
    inventors = inventors.explode('biblio.parties.inventors')

    inventors_normalized = []
    for inventor in inventors['biblio.parties.inventors']:
        if isinstance(inventor, dict) or (isinstance(inventor, list) and all(isinstance(i, dict) for i in inventor)):
            inventor_normalized = pd.json_normalize(inventor)
            inventors_normalized.append(inventor_normalized)
        else:
            inventor_normalized = pd.DataFrame({'extracted_name.value': [None], 'residence': [None], 'sequence': [None]})
            inventors_normalized.append(inventor_normalized)
    inventors_normalized = pd.concat(inventors_normalized, axis=0)
    inventors_normalized = inventors_normalized.reset_index(drop=True)
    inventors = inventors.reset_index(drop=True)
    inventors = pd.concat([inventors[['lens_id', 'doc_key']], inventors_normalized], axis=1)
    inventors = inventors[['lens_id', 'doc_key', 'extracted_name.value', 'residence', 'sequence']]
    inventors.rename(columns={'extracted_name.value': 'extracted_name'}, inplace=True)
    inventors.rename(columns={'sequence': 'inventor_sequence'}, inplace=True)
    return inventors

def clean_company_name(name):
    stopwords = ['oy', 'ab', 'ky', 'oyj', 'gmbh', 'ltd', 'rf', 'seura', 'r s sr', 'ry', 'r y',
                 'asunto oy', 'as oy', 'kiinteistö oy', 'ja', 'tmi', 't mi']
    name = name.lower()
    name = re.sub(r'[^a-z0-9åäöü]', ' ', name)
    name = re.sub(r'[ ]{2+}', ' ', name)
    name = re.sub(r'(\b' + r'\b|\b'.join(stopwords) + r'\b)', ' ', name)
    return name
