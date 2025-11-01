import requests
import dotenv
import json
import time
import os
import record_detail

dotenv.load_dotenv()

class Europeana:
    def __init__(self):
        self.api_key = dotenv.get_key(
            dotenv.find_dotenv(),
            "EUROPEANA_API_KEY"
        )

    def fetch_europeana_data(self, **query_params):
        url = "https://api.europeana.eu/record/v2/search.json"
        query_params['wskey'] = self.api_key
        response = requests.get(url, params=query_params, timeout=30)
        response.raise_for_status()
        return response.json()


    def get_basic_metadata(self, record):
        base = {
            'id': record.get('id', 'No id'),
            'title': record.get('title', ['No Title']),
            'creator': record.get('dcCreator', ['Unknown Creator']),
            'description': record.get('dcDescription', ['No Description'])[0],
            'year': record.get('year', ['Unknown Year'])[0],
            'timespan': record.get('edmTimespanLabelLangAware', {}).get('en', ['Unknown Timespan']),
            'language': record.get('language', ['Unknown Language']),
            'type': record.get('type', ['Unknown Type']),
            'concepts': [c["def"] for c in record.get("edmConceptLabel", []) if "def" in c],
            'place': record.get("edmPlaceLabelLangAware", {}),
            'place_lat': record.get("edmPlaceLatitude", [None])[0],
            'place_lon': record.get('edmPlaceLongitude', [None])[0],
            'country': record.get('country', ['No Country'])[0],
            'collection': record.get('europeanaCollectionName', ['No Collection'])[0],
            "thumbnail": record.get("edmPreview", [None])[0],
            "link": record.get("edmIsShownAt", [None])[0],
            "rights": record.get("rights", [None])[0],
        }

        return base

    def get_metadata_by_collection(self, collection_name, rows=24, start=1):
        data = self.fetch_europeana_data(
        query="*",
        qf=[
            'LANGUAGE:"en"',
            'LANGUAGE:"es"',
            'TYPE:"TEXT"',
            'MIME_TYPE:"image/jpeg"',
            f'collection:{collection_name}'
        ],
        rows=rows,
        reusability="open",
        start=start,
        media='true'
        )   

        metadata = []

        for entry in data.get('items', []):
            metadata.append(self.get_basic_metadata(entry))

        return metadata

    def enrich_record(self, record_object):

        item_id = record_object.get('id')
        try:
            record = record_detail.Europeana()
            obj = record.record_detail(item_id)

            iiif = record.get_iiif_manifest(obj)

            dates = record.normalize_date(obj)

            locations = record.extract_place(obj)

            creators = record.extract_creators(obj) or record_object.get("creator") or []

            record_object.update({
                "iiif_manifest": iiif,
                "creators": creators,
                "year": dates["year"] or record_object.get("year"),
                "date_begin": dates["date_begin"],
                "date_end": dates["date_end"],
                "place_label": locations["place"] or record_object.get("place") or None,
                "place_lat": locations["place_lat"] or record_object.get("place_lat"),
                "place_lon": locations["place_lon"] or record_object.get("place_lon"),
                })
            
            return record_object

        except Exception as e:
            raise

    def get_all_collections(self, collections: list, savefile=True):
        all_metadata = []

        for collection in collections:
            time.sleep(1)
            print(f"Fetching metadata for collection: {collection}")
            batch = self.get_metadata_by_collection(collection)
            print(f"Got {len(batch)} items. Enriching with record details...")
            for rec in batch:
                time.sleep(0.15)
                enriched = self.enrich_record(rec)
                all_metadata.append(enriched)

        print(f"Total records fetched: {len(all_metadata)}")

        if savefile:
            os.makedirs('data/metadata', exist_ok=True)
            with open('data/metadata/europeana_metadata.json', 'w', encoding='utf-8') as file:
                json.dump(all_metadata, file, indent=4, ensure_ascii=False)
        else:
            return all_metadata


if __name__ == "__main__":
    collections = [
        'industrial',
        'art',
        'manuscript',
        'map',
        'migration',
        'music'
    ]

    europeana = Europeana()
    europeana.get_all_collections(collections, savefile=True)