#!/usr/bin/env python3
"""
Upload sc1-data-format schema to Supabase
This script reads format.json and uploads the field definitions to Supabase
so that telemetry data can be properly parsed in queries
"""

import json
import sys
from pathlib import Path

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

def load_format_json(format_path: str = "sc1-data-format/format.json"):
    """Load and parse format.json"""
    path = Path(format_path)
    if not path.exists():
        print(f"Error: {format_path} not found")
        sys.exit(1)
    
    with open(path, 'r') as f:
        return json.load(f)

def convert_to_schema_format(format_data: dict) -> list:
    """Convert format.json structure to schema format for reference"""
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
            "num_bytes": num_bytes,
            "data_type": data_type,
            "units": units,
            "nominal_min": nominal_min,
            "nominal_max": nominal_max,
            "category": category,
            "offset": offset,
        })
        
        offset += num_bytes
    
    return fields

def upload_to_supabase(supabase: Client, fields: list, format_version: str = "1.0"):
    """Upload format schema to Supabase telemetry_schema table"""
    try:
        # First, check if we need to clear existing schema
        existing = supabase.table('telemetry_schema').select('id').limit(1).execute()
        
        if existing.data:
            print("Clearing existing schema entries...")
            supabase.table('telemetry_schema').delete().neq('id', 0).execute()
        
        # Insert new schema fields
        for field in fields:
            field['format_version'] = format_version
        
        result = supabase.table('telemetry_schema').insert(fields).execute()
        
        print(f"✅ Successfully uploaded format schema v{format_version}")
        print(f"   Total fields: {len(fields)}")
        print(f"   Total bytes: {fields[-1]['offset'] + fields[-1]['num_bytes']}")
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

def main():
    """Main function"""
    print("SC1 Data Format → Supabase Schema Uploader")
    print("=" * 50)
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found")
        return
    
    supabase_url = config.get('supabase_url', '')
    supabase_key = config.get('supabase_anon_key', '')
    
    if not supabase_url or not supabase_key:
        print("❌ supabase_url or supabase_anon_key not set in config.json")
        return
    
    print(f"Supabase URL: {supabase_url}")
    print()
    
    # Create Supabase client
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {e}")
        return
    
    # Load format.json
    print("Loading sc1-data-format/format.json...")
    format_data = load_format_json()
    print(f"✅ Loaded {len(format_data)} fields")
    print()
    
    # Convert to schema format
    print("Converting to schema format...")
    fields = convert_to_schema_format(format_data)
    total_bytes = fields[-1]['offset'] + fields[-1]['num_bytes']
    print(f"✅ Total packet size: {total_bytes} bytes")
    print()
    
    # Show sample fields
    print("Sample fields:")
    for field in fields[:5]:
        print(f"  - {field['name']}: {field['data_type']} @ offset {field['offset']} ({field['num_bytes']} bytes)")
    print(f"  ... and {len(fields) - 5} more")
    print()
    
    # Upload to Supabase
    print("Uploading to Supabase...")
    success = upload_to_supabase(supabase, fields)
    
    if success:
        print()
        print("✅ Setup complete!")
        print()
        print("You can now:")
        print("  1. Send telemetry data from the car")
        print("  2. Query data using Supabase client or REST API")
        print("  3. Create real-time subscriptions for live data")
        print()
        print("Example query in Python:")
        print("  from supabase import create_client")
        print("  supabase = create_client(url, key)")
        print("  data = supabase.table('telemetry').select('*').order('timestamp', desc=True).limit(100).execute()")
    else:
        print()
        print("⚠️  Upload failed. Please check:")
        print("  1. Supabase project is running")
        print("  2. Tables are created (run the SQL schema)")
        print("  3. Internet connection is working")
        print("  4. API keys are correct")

if __name__ == "__main__":
    main()
