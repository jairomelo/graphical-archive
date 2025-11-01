import requests
import dotenv
import re
import os
import json
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

class Europeana:
    def __init__(self):
        self.api_key = dotenv.get_key(
            dotenv.find_dotenv(),
            "EUROPEANA_API_KEY"
        )

    def record_detail(self, record_id):
        url = f"https://api.europeana.eu/record/v2/{record_id}.json"
        params = {
            'wskey': self.api_key
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('object', {})   
    
    def pick_labels_by_language(self, record_object, langs=['en', 'es']):
        out = []
        pref = record_object.get("prefLabel") or {}
        for lang in langs:
            vals = pref.get(lang)
            if isinstance(vals, list):
                out.extend([v for v in vals if v not in out])
        return out
    
    def get_iiif_manifest(self, record_object):
        
        aggs = record_object.get("aggregations") or []
        for agg in aggs:
            for wr in agg.get("webResources", []):
                for key in ("dctermsIsReferencedBy", "dcterms:isReferencedBy"):
                    manifest_url = wr.get(key)
                    if isinstance(manifest_url, list) and manifest_url:
                        return manifest_url[0]
                    if isinstance(manifest_url, str) and manifest_url:
                        return manifest_url
        return None
    
    def normalize_date(self, obj: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Extract a single 'year' plus optional begin/end from 'timespans' or proxies."""
        year = None
        date_begin = None
        date_end = None

        # Prefer explicit timespans with begin/end
        for ts in obj.get("timespans", []):
            begin = (ts.get("begin") or {}).get("def", [None])[0]
            end   = (ts.get("end") or {}).get("def", [None])[0]
            if begin or end:
                date_begin = date_begin or begin
                date_end   = date_end   or end
            # Literal year sometimes sits in skosNotation/def
            lit = (ts.get("skosNotation") or {}).get("def", [None])[0]
            if lit and re.fullmatch(r"\d{3,4}", lit):
                year = year or lit

        # Fallback: Europeana proxies often have 'year' or 'dcDate'
        for px in obj.get("proxies", []):
            y = (px.get("year") or {}).get("def", [None])[0]
            if y and re.fullmatch(r"\d{3,4}", y):
                year = year or y
            d = (px.get("dcDate") or {}).get("def", [None])[0]
            if d and re.fullmatch(r"#?\d{3,4}", d):
                year = year or d.lstrip("#")

        return {"year": year, "date_begin": date_begin, "date_end": date_end}
    
    def extract_place(self, obj: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Prefer concrete place from 'places' (label + coords); fallback to europeanaAggregation.edmCountry."""
        places = obj.get("places") or []
        if places:
            p0 = places[0]
            labels = self.pick_labels_by_language(p0)
            lat = p0.get("latitude")
            lon = p0.get("longitude")
            return {"place": labels[0] if labels else None, "place_lat": lat, "place_lon": lon}
        eagg = obj.get("europeanaAggregation") or {}
        country = (eagg.get("edmCountry") or {}).get("def", [None])[0]
        return {"place": country, "place_lat": None, "place_lon": None}

    def extract_creators(self, obj: Dict[str, Any]) -> List[str]:
        """Turn agent URIs into readable labels using agents[*].prefLabel."""
        out = []
        for a in obj.get("agents", []):
            labels = self.pick_labels_by_language(a)
            out.extend(labels)
        return list(dict.fromkeys(out))


