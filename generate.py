# Generate citation graph from CORD-19 dataset.
# Outputs a gexf file.
# ---
# Since there are many papers with similar titles but they exist
# in the dataset in duplicates (eg. preprints, typos in title),
# we try to merge them.
# Step 1: iterate through the metadata file to generate base nodes and title map mapping title to nodes
# Step 2: iterate through each node with the paper json files, add citation edges, but check for similar titles in the title map to avoid creating duplicate node
# Step 3: pass the graph to networkx and do some postprocessing operations

import pandas as pd
import datetime
import os
import json
import math
import networkx as nx
import heapq

PATH_CORD_DATA_ROOT = 'cord-2020-06-02'
PATH_CORD_METADATA_CSV = os.path.join(PATH_CORD_DATA_ROOT, 'metadata.csv')

def main():
    df = get_cord_metadata_df(PATH_CORD_METADATA_CSV)
    title_map = get_title_map(df)
    citations = get_citations(df, title_map)
    print('All Papers:', len(df), 'All Citations:', len(citations))
    nx_graph = get_networkx_graph(df, title_map, citations)
    # If you want the whole graph without our post processing, comment out the next line
    nx_graph = post_processing_nx_graph(nx_graph)
    # Save to gexf
    nx.write_gexf(nx_graph, 'cord19.gexf')

def get_cord_metadata_df(path):
    df = pd.read_csv(path, header=0)
    r, c = df.shape
    print('Before processing, row =', r, 'column =', c)
    # These columns are not so useful.
    df.drop(['sha', 'mag_id', 'who_covidence_id', 'arxiv_id', 's2_id'], axis=1, inplace=True)
    # Filter out super short error titles
    # there are many of them in the data.
    df['title'] = df['title'].astype('str')
    df = df.loc[df['title'].str.len() > 20]
    # Filter out papers that are not from 2020
    # since we only want COVID-19 papers.
    df = df[pd.to_datetime(df['publish_time'], infer_datetime_format=True) > '12-31-2019']

    df = df.sort_values(by=['title']).reset_index(drop=True)
    
    r, c = df.shape
    print('After processing, row =', r, 'column =', c)

    return df

# Returns true if two titles are considered similar
def are_titles_similar(title1, title2):
    t1 = title1.lower().strip()
    t2 = title2.lower().strip()
    # Reply papers don't fit the rule below.
    if ('reply' in t1 or 'reply' in t2):
        return False
    similar = False

    if len(t1) > len(t2):
        if len(t1) - len(t2) > 20:
            return False
        if t1[:len(t2)] == t2:
            similar = True
    else:
        if len(t2) - len(t1) > 20:
            return False
        if t2[:len(t1)] == t1:
            similar = True
        
    # if similar:
    #     print('Found similar titles: ', title1, ' vs. ', title2)
    return similar

# Returns a map <title, df index>
def get_title_map(df):
    title_map = dict()

    for row in df.itertuples():
        index = row.Index
        current_title = row.title
        hasSimilar = False
        # If a similar title exists, point to the existing entry
        # for key, value in title_map.items():
        #     if key == current_title or are_titles_similar(key, current_title):
        #         title_map[current_title] = value
        #         hasSimilar = True
        #         break
        if index != 0:
            prior = df.iloc[index - 1]
            prior_title = prior['title']
            if current_title == prior_title or are_titles_similar(current_title, prior_title):
                title_map[current_title] = title_map[prior_title]
                continue
        # If a similar title does not exist, add a new entry
        title_map[current_title] = index
    return title_map

# Returns a list of edges represented by list [[from df index, to df index], [from, to], ...]
def get_citations(df, title_map):
    citations = []
    for row in df.itertuples():
        fromIdx = title_map[row.title]
        # CORD-19 recommends pmc over pdf json files when present
        jsonFilePath = row.pmc_json_files
        if not isinstance(jsonFilePath, str) or jsonFilePath == '':
            jsonFilePath = row.pdf_json_files
        if not isinstance(jsonFilePath, str) or jsonFilePath == '':
            continue
        # some of the path separate multiple paths by ;
        jsonFilePath = jsonFilePath.split(';')[0]
        jsonFilePath = os.path.join(PATH_CORD_DATA_ROOT, jsonFilePath)
        citation_titles = get_citation_titles_from_json_file(jsonFilePath)
        for cited_title in citation_titles:
            if cited_title in title_map:
                citations.append([fromIdx, title_map[cited_title]])
            # else:
            #     for key, value in title_map.items():
            #         if are_titles_similar(key, cited_title):
            #             citations.append([fromIdx, value])
            #             break
    return citations

def get_citation_titles_from_json_file(jsonFilePath):
    print('Retrieving citations from JSON file:', jsonFilePath)
    citation_titles = []
    with open(jsonFilePath) as f:
        data = json.load(f)
        bib_entries = data['bib_entries']
        for bibref in bib_entries.values():
            citation_titles.append(bibref['title'])     
    return citation_titles

def get_networkx_graph(df, title_map, citations):
    nx_graph = nx.Graph()
    nodeAdded = set()

    # Add edges
    for citation in citations:
        fromIdx = citation[0]
        toIdx = citation[1]
        if not (fromIdx in nodeAdded):
            nodeAdded.add(fromIdx)
            row = df.iloc[fromIdx]
            attrdict = dict()
            attrdict['title'] = str(row['title'])
            attrdict['cord_uid'] = str(row['cord_uid'])
            attrdict['doi'] = str(row['doi'])
            attrdict['abstract'] = str(row['abstract'])
            attrdict['publish_time'] = str(row['publish_time'])
            attrdict['authors'] = str(row['authors'])
            attrdict['journal'] = str(row['journal'])
            attrdict['url'] = str(row['url'])
            nx_graph.add_node(fromIdx, **attrdict)
        if not (toIdx in nodeAdded):
            nodeAdded.add(toIdx)
            row = df.iloc[toIdx]
            attrdict = dict()
            attrdict['title'] = str(row['title'])
            attrdict['cord_uid'] = str(row['cord_uid'])
            attrdict['doi'] = str(row['doi'])
            attrdict['abstract'] = str(row['abstract'])
            attrdict['publish_time'] = str(row['publish_time'])
            attrdict['authors'] = str(row['authors'])
            attrdict['journal'] = str(row['journal'])
            attrdict['url'] = str(row['url'])
            nx_graph.add_node(toIdx, **attrdict)
            
        nx_graph.add_edge(fromIdx, toIdx)

    return nx_graph

def post_processing_nx_graph(G):
    G = G.subgraph(max(nx.connected_components(G), key=len))
    # Compute pagerank
    pr = nx.pagerank(G, weight=None)
    nodes = heapq.nlargest(500, pr, key=pr.get)
    G = G.subgraph(nodes)
    i = 0
    for n in G:
        G.nodes[n]['id'] = i
        i = i + 1
    return G

if __name__ == "__main__":
    main()