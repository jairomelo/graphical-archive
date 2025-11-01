import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

df = pd.read_json('data/metadata/europeana_metadata.json')

df.head().to_csv('data/metrics/europeana_metadata.csv', index=False)

df['concepts'] = df['concepts'].apply(lambda x: ' '.join(x) if isinstance(x, list) else '')
df['title'] = df['title'].apply(lambda x: ' '.join(x) if isinstance(x, list) else '')
df['description'] = df['description'].apply(lambda x: x if isinstance(x, str) else '') 

df['text'] = df['concepts'] + ' ' + df['title'] + ' ' + df['description']

vec = TfidfVectorizer(stop_words='english', max_features=5000, min_df=2)
X = vec.fit_transform(df['text'])

k = 6
km = KMeans(n_clusters=k, random_state=0).fit(X)
df['cluster'] = km.labels_

tsne = TSNE(perplexity=15, random_state=0)
xy = tsne.fit_transform(X.toarray())
plt.figure(figsize=(10, 8))
plt.scatter(xy[:,0], xy[:,1], c=df.cluster, cmap='tab10')
plt.title('t-SNE visualization of Europeana records clusters')

os.makedirs('data/metrics', exist_ok=True)
plt.savefig('data/metrics/europeana_clusters.png')
df.to_csv('data/metrics/europeana_clusters.csv', index=False)