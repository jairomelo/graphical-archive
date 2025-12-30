import json
import math
import os
from pathlib import Path
import ast

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

##### Load metadata #####

df = pd.read_json('static/data/europeana_metadata.json')

df['title'] = df['title'].apply(lambda x: ' '.join(x) if isinstance(x, list) else '')
df['concepts'] = df['concepts'].apply(lambda x: ' '.join(x) if isinstance(x, list) else '')
df['description'] = df['description'].apply(lambda x: ' '.join(x) if isinstance(x, list) else '')
df['place_label'] = df['place_label'].apply(lambda x: ' '.join(x) if isinstance(x, list) else '')

df['year'] = pd.to_numeric(df['year'].replace('Unknown Year', None), errors='coerce')

for c in ['date_begin', 'date_end']:
    df[c] = pd.to_datetime(df[c], errors='coerce')

df = df[['id', 'title', 'description', 'concepts', 'year', 'date_begin', 'date_end', 
         'place_label', 'place_lat', 'place_lon', 'country', 'collection']]

#### Build text vectors #####

df['text'] = df['title'] + ' ' + df['concepts'] + ' ' + df['description'] + ' ' + df['place_label']

try:
    vec = TfidfVectorizer(stop_words='english', max_features=5000, min_df=2)
    X = vec.fit_transform(df['text'])
    if X.shape[1] == 0:
        raise ValueError("Empty vocabulary with min_df=2.")
except Exception:
    vec = TfidfVectorizer(stop_words='english', max_features=5000, min_df=1)
    X = vec.fit_transform(df['text'])

# Cosine similarity of TF–IDF vectors of titles, descriptions, concepts.
S_text = cosine_similarity(X)

#### Build temporal similarity #####
n = len(df)
S_date = np.zeros((n,n), dtype=float)

# exponential kernel with 25 years bandwidth
bandwidth = 25.0

def get_temporal_range(row):
    """
    Extract temporal range for an item, using year, date_begin, and date_end.
    Returns (min_year, max_year) tuple or (None, None) if no temporal info available.
    """
    year = row['year']
    date_begin = row['date_begin']
    date_end = row['date_end']
    
    # Priority 1: Use exact year if available
    if not pd.isna(year):
        return (year, year)
    
    # Priority 2: Use date range if both available
    if not pd.isna(date_begin) and not pd.isna(date_end):
        return (date_begin.year, date_end.year)
    
    # Priority 3: Use single date as point
    if not pd.isna(date_begin):
        return (date_begin.year, date_begin.year)
    
    if not pd.isna(date_end):
        return (date_end.year, date_end.year)
    
    # No temporal information available
    return (None, None)

def calculate_temporal_distance(t_min_i, t_max_i, t_min_j, t_max_j):
    """
    Calculate minimum distance between two temporal ranges.
    Returns 0 if ranges overlap.
    """
    if t_max_i < t_min_j:
        # Range i is entirely before range j
        return t_min_j - t_max_i
    elif t_max_j < t_min_i:
        # Range j is entirely before range i
        return t_min_i - t_max_j
    else:
        # Ranges overlap
        return 0

# Calculate temporal similarity matrix with range awareness
for i in range(n):
    t_min_i, t_max_i = get_temporal_range(df.iloc[i])
    
    if t_min_i is None:
        continue  # No temporal info for item i
    
    for j in range(i, n):
        t_min_j, t_max_j = get_temporal_range(df.iloc[j])
        
        if t_min_j is None:
            continue  # No temporal info for item j
        
        # Calculate minimum distance between temporal ranges
        distance = calculate_temporal_distance(t_min_i, t_max_i, t_min_j, t_max_j)
        
        # Apply exponential kernel
        similarity = np.exp(-distance / bandwidth)
        
        S_date[i, j] = similarity
        S_date[j, i] = similarity  # Symmetric matrix

#### Define spatial proximity #####

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

coords = df[['place_lat', 'place_lon']].to_numpy()
S_place = np.zeros((n,n), dtype=float)
sigma = 400.0  # bandwidth in kilometers

for i in range(n):
    lat1, lon1 = coords[i]
    if pd.isna(lat1) or pd.isna(lon1):
        continue
    for j in range(i, n):
        lat2, lon2 = coords[j]
        if np.isnan(lat2) or np.isnan(lon2):
            continue
        d = haversine(lat1, lon1, lat2, lon2)
        s = math.exp(-d / sigma)
        S_place[i, j] = s
        S_place[j, i] = s

# Normalize similarity matrices to [0, 1]
if n > 1:
    scaler = MinMaxScaler()
    S_date = scaler.fit_transform(S_date)
    S_place = scaler.fit_transform(S_place)


#### Create the Good Neihbor Index #####
alpha, beta, gamma = 0.6, 0.2, 0.2 # these weights can be adjusted

# Formula

G = alpha * S_text + beta * S_date + gamma * S_place

# Build neighbors: top 10 neighbors for each record
top_k = 10
neighbors = {}
edges_rows = []

for i, row in df.iterrows():
    scores = G[i].copy()
    scores[i] = -1  # exclude self
    top_idx = np.argsort(scores)[-top_k:][::-1] # indices of top k neighbors
    items = []
    for j in top_idx:
        items.append({
            "id": df.loc[j, "id"],
            "score": float(scores[j]),
            "S_text": float(S_text[i, j]),
            "S_date": float(S_date[i, j]),
            "S_place": float(S_place[i, j]),
            "title": df.loc[j, "title"]
        })
        edges_rows.append({
            "source": df.loc[i, "id"],
            "target": df.loc[j, "id"],
            "G": float(scores[j]),
            "S_text": float(S_text[i, j]),
            "S_date": float(S_date[i, j]),
            "S_place": float(S_place[i, j])
        })
    neighbors[df.loc[i, "id"]] = items

# Save neighbors to JSON  
out_dir = Path('static/data')
os.makedirs(out_dir, exist_ok=True)

with open(out_dir / 'europeana_neighbors.json', 'w', encoding='utf-8') as f:
    json.dump(neighbors, f, ensure_ascii=False, indent=2)