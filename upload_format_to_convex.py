#!/usr/bin/env python3
"""
Upload sc1-data-format schema to Convex
This script reads format.json and uploads the field definitions to Convex
so that telemetry data can be properly parsed in queries
"""

import json
import sys
import requests
from pathlib import Path

def load_format_json(format_path: str = "sc1-data-format/format.json"):
    """Load and parse format.json"""
    path = Path(format_path)
    if not path.exists():
        print(f"Error: {format_path} not found")
        sys.exit(1)
    
    with open(path, 'r') as f:
        return json.load(f)

def convert_to_convex_format(format_data: dict) -> list:
    """Convert format.json structure to Convex schema format"""
    fields = []
    offset = 0
    
    for name, field_info in format_data.items():
        # format.json structure: [num_bytes, data_type, units, nominal_min, nominal_max, category]
        num_bytes = field_info[0]
        data_type = field_info[1]
        units = field_info[2]
        nominal_min = field_info[3]
        nominal_max = field_info[4]
        category = field_info[5]
        
        fields.append({
            "name": name,
            "numBytes": num_bytes,
            "dataType": data_type,
            "units": units,
            "nominalMin": nominal_min,
            "nominalMax": nominal_max,
            "category": category,
            "offset": offset,
        })
        
        offset += num_bytes
    
    return fields

def upload_to_convex(convex_url: str, fields: list, format_version: str = "1.0"):
    """Upload format schema to Convex"""
    payload = {
        "path": "telemetryParser:uploadFormatSchema",
        "args": [{
            "formatVersion": format_version,
            "fields": fields,
        }]
    }
    
    url = f"{convex_url}/api/mutation"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code >= 200 and response.status_code < 300:
            result = response.json()
            print(f"✅ Successfully uploaded format schema v{format_version}")
            print(f"   Total fields: {len(fields)}")
            print(f"   Total bytes: {fields[-1]['offset'] + fields[-1]['numBytes']}")
            print(f"   Response: {result}")
            return True
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Main function"""
    print("SC1 Data Format → Convex Schema Uploader")
    print("=" * 50)
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found")
        return
    
    convex_url = config.get('convex_deployment_url', '')
    
    if not convex_url:
        print("❌ convex_deployment_url not set in config.json")
        return
    
    print(f"Convex URL: {convex_url}")
    print()
    
    # Load format.json
    print("Loading sc1-data-format/format.json...")
    format_data = load_format_json()
    print(f"✅ Loaded {len(format_data)} fields")
    print()
    
    # Convert to Convex format
    print("Converting to Convex schema format...")
    fields = convert_to_convex_format(format_data)
    total_bytes = fields[-1]['offset'] + fields[-1]['numBytes']
    print(f"✅ Total packet size: {total_bytes} bytes")
    print()
    
    # Show sample fields
    print("Sample fields:")
    for field in fields[:5]:
        print(f"  - {field['name']}: {field['dataType']} @ offset {field['offset']} ({field['numBytes']} bytes)")
    print(f"  ... and {len(fields) - 5} more")
    print()
    
    # Upload to Convex
    print("Uploading to Convex...")
    success = upload_to_convex(convex_url, fields)
    
    if success:
        print()
        print("✅ Setup complete!")
        print()
        print("You can now:")
        print("  1. Send telemetry data from the car")
        print("  2. Query parsed data using telemetryParser:parseTelemetryData")
        print("  3. Get time-series data using telemetryParser:getParsedTelemetryByTimeRange")
        print()
        print("Example query in Convex dashboard:")
        print('  telemetryParser:getParsedTelemetryByTimeRange({')
        print('    startTime: Date.now() - 3600000,  // Last hour')
        print('    endTime: Date.now(),')
        print('    fields: ["speed", "soc", "pack_voltage"]')
        print('  })')
    else:
        print()
        print("⚠️  Upload failed. Please check:")
        print("  1. Convex deployment is running")
        print("  2. telemetryParser.ts is deployed to Convex")
        print("  3. Internet connection is working")

if __name__ == "__main__":
    main()
