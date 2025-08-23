#!/usr/bin/env python3
"""
Simple KML -> GeoJSON converter for points and lines (no external deps).
Usage:
  python kml_to_geojson.py "path/to/input.kml" "path/to/output.geojson"

Produces a FeatureCollection with properties: name, description, styleUrl, and any ExtendedData fields.
"""
import sys
import os
import json
import xml.etree.ElementTree as ET

KML_NS = '{http://www.opengis.net/kml/2.2}'

def parse_coordinates(text):
    if not text:
        return []
    coords = []
    # KML coordinates use lon,lat[,alt] tuples separated by whitespace/newlines
    for part in text.strip().split():
        parts = [p for p in part.split(',') if p != '']
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                coords.append([lon, lat])
            except ValueError:
                continue
    return coords


def placemark_to_feature(pm):
    name_el = pm.find(KML_NS + 'name')
    desc_el = pm.find(KML_NS + 'description')
    style_el = pm.find(KML_NS + 'styleUrl')
    props = {}
    if name_el is not None and name_el.text:
        props['name'] = name_el.text.strip()
    if desc_el is not None and desc_el.text:
        props['description'] = desc_el.text.strip()
    if style_el is not None and style_el.text:
        props['styleUrl'] = style_el.text.strip()
    # ExtendedData
    ed = pm.find(KML_NS + 'ExtendedData')
    if ed is not None:
        for data in ed.findall(KML_NS + 'Data'):
            key = data.get('name')
            value_el = data.find(KML_NS + 'value')
            if key:
                props[key] = value_el.text.strip() if (value_el is not None and value_el.text) else ''
    # geometry
    point = pm.find('.//' + KML_NS + 'Point')
    if point is not None:
        coords_text = (point.find(KML_NS + 'coordinates').text if point.find(KML_NS + 'coordinates') is not None else '')
        coords = parse_coordinates(coords_text)
        if coords:
            return {
                'type': 'Feature',
                'properties': props,
                'geometry': {'type': 'Point', 'coordinates': coords[0]}
            }
    linestring = pm.find('.//' + KML_NS + 'LineString')
    if linestring is not None:
        coords_text = (linestring.find(KML_NS + 'coordinates').text if linestring.find(KML_NS + 'coordinates') is not None else '')
        coords = parse_coordinates(coords_text)
        if coords:
            return {
                'type': 'Feature',
                'properties': props,
                'geometry': {'type': 'LineString', 'coordinates': coords}
            }
    polygon = pm.find('.//' + KML_NS + 'Polygon')
    if polygon is not None:
        outer = polygon.find('.//' + KML_NS + 'outerBoundaryIs')
        if outer is not None:
            coords_el = outer.find('.//' + KML_NS + 'coordinates')
            coords = parse_coordinates(coords_el.text if coords_el is not None else '')
            if coords:
                return {
                    'type': 'Feature',
                    'properties': props,
                    'geometry': {'type': 'Polygon', 'coordinates': [coords]}
                }
    # fallback: no geometry
    return None


def convert(in_path, out_path):
    tree = ET.parse(in_path)
    root = tree.getroot()
    features = []
    # iterate Placemark elements anywhere under the document
    for pm in root.findall('.//' + KML_NS + 'Placemark'):
        feat = placemark_to_feature(pm)
        if feat:
            features.append(feat)
    fc = {'type': 'FeatureCollection', 'features': features}
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    return len(features)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: kml_to_geojson.py INPUT.kml OUTPUT.geojson')
        sys.exit(2)
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    if not os.path.isfile(in_file):
        print('Input file not found:', in_file)
        sys.exit(1)
    n = convert(in_file, out_file)
    print(f'Converted {n} features to', out_file)
