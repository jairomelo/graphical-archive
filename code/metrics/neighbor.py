import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

##### Load Custom Gazetteer #####
with open('static/data/gazetteer.json', 'r', encoding='utf-8') as f:
    gazetteer = json.load(f)

##### Load metadata #####

df = pd.read_json('static/data/europeana_metadata.json')

def handle_scalar_values(func):
    def wrapper(value):
        if value is None:
            return ''
        try:
            if pd.isna(value):
                return ''
        except (ValueError, TypeError):
            pass
        return func(value)
    return wrapper

@handle_scalar_values
def extract_text_field(field):
    """Extract text from a field that may be a string, list, or dict."""
    
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        return ' '.join(str(item) for item in field if item)
    if isinstance(field, dict):
        for lang in ['en', 'fr', 'de']:
            if lang in field and field[lang]:
                value = field[lang]
                if isinstance(value, list):
                    return ' '.join(str(item) for item in value if item)
                return str(value)
        
        values = [str(v) for v in field.values() if v]
        return ' '.join(values) if values else ''
    
    return str(field)
                
@handle_scalar_values
def extract_place_name(place_label):
    """Extract consistent place name for gazetteer lookup."""
    if isinstance(place_label, str):
        return place_label
    if isinstance(place_label, list):
        return str(place_label[0]) if place_label else ''
    if isinstance(place_label, dict):
        place_name = place_label.get('en')
        if not place_name or place_name == 'Unknown':
            place_name = next(iter(place_label.values()), 'Unknown')
        return str(place_name) if place_name else ''
    return str(place_label)

#### Preprocess DataFrame #####

df['title'] = df['title'].apply(extract_text_field)
df['concepts'] = df['concepts'].apply(extract_text_field)
df['description'] = df['description'].apply(extract_text_field)
df['place_label'] = df['place_label'].apply(extract_place_name)


df['year'] = pd.to_numeric(df['year'].replace('Unknown Year', None), errors='coerce')

for c in ['date_begin', 'date_end']:
    df[c] = pd.to_datetime(df[c], errors='coerce')

df = df[['id', 'title', 'description', 'concepts', 'year', 'date_begin', 'date_end', 
         'place_label', 'place_lat', 'place_lon', 'country', 'collection']]

#### Handle missing coordinates using gazetteer #####
for idx, row in df.iterrows():
    if pd.notna(row['place_lat']) and pd.notna(row['place_lon']):
        continue  # Coordinates already present
    
    place_name = row['place_label']
    
    if place_name and place_name in gazetteer:
        gaz_entry = gazetteer[place_name]
        df.at[idx, 'place_lat'] = gaz_entry.get('place_lat')
        df.at[idx, 'place_lon'] = gaz_entry.get('place_lon')

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
alpha, beta, gamma, delta = 0.5, 0.2, 0.2, 0.1 # predefined weights

# Formula: G = α·S_text + β·S_date + γ·S_place + δ·S_user

G = alpha * S_text + beta * S_date + gamma * S_place + delta * 0  # No user similarity for now

# Build neighbors: top 50 neighbors for each record
top_k = 50
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