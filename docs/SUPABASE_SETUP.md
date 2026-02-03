# Supabase Setup Guide

This guide explains how to set up Supabase for storing telemetry data from the SC2 solar car.

## Prerequisites

- A [Supabase](https://supabase.com) account (free tier available)
- Python 3.8+ with pip (for the upload script)

## Quick Start

### 1. Create a Supabase Project

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Enter a project name and database password
4. Select a region close to your location
5. Wait for the project to be created (~2 minutes)

### 2. Set Up the Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Copy and paste the contents of `docs/supabase-schema.sql`
3. Click "Run" to create the tables

### 3. Get Your API Credentials

1. Go to **Settings** → **API** in your Supabase dashboard
2. Copy these values:
   - **Project URL** (e.g., `https://abcdefgh.supabase.co`)
   - **anon public** key (starts with `eyJ...`)

### 4. Configure the Application

Update your `config.json` with the Supabase credentials:

```json
{
    "supabase_url": "https://your-project-id.supabase.co",
    "supabase_anon_key": "your-anon-key-here",
    "supabase_table_name": "telemetry",
    "supabase_timeout_ms": 5000,
    "supabase_retry_interval_ms": 3000
}
```

### 5. Upload the Format Schema (Optional)

Install the Python dependencies and upload the schema:

```bash
pip install supabase
python upload_format_to_supabase.py
```

## Real-time Subscriptions

Supabase supports real-time data subscriptions. To enable:

1. Go to **Database** → **Replication** in your dashboard
2. Enable replication for the `telemetry` table
3. Use the Supabase client library to subscribe to changes

Example (JavaScript):
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

supabase
  .channel('telemetry_changes')
  .on('postgres_changes', { 
    event: 'INSERT', 
    schema: 'public', 
    table: 'telemetry' 
  }, (payload) => {
    console.log('New telemetry:', payload.new)
  })
  .subscribe()
```

## Querying Data

### REST API

```bash
# Get latest 100 records
curl "https://your-project.supabase.co/rest/v1/telemetry?order=timestamp.desc&limit=100" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Get records in time range
curl "https://your-project.supabase.co/rest/v1/telemetry?timestamp=gte.1706900000000&timestamp=lte.1706910000000" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### Python

```python
from supabase import create_client

supabase = create_client(url, key)

# Get latest records
data = supabase.table('telemetry').select('*').order('timestamp', desc=True).limit(100).execute()

# Get specific fields
data = supabase.table('telemetry').select('timestamp, speed, soc, pack_voltage').execute()

# Filter by time range
data = supabase.table('telemetry').select('*').gte('timestamp', start_time).lte('timestamp', end_time).execute()
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit** your `config.json` with real API keys to public repositories
2. The `anon` key is meant for public access but is still sensitive
3. For production, consider using a `service_role` key server-side
4. Row Level Security (RLS) policies are enabled by default

## Troubleshooting

### Data not appearing
- Check that the table was created correctly
- Verify API keys are correct
- Check network connectivity from the car

### Permission denied errors
- Ensure RLS policies are set up correctly
- Check the API key has proper permissions

### Slow queries
- Add indexes for frequently queried columns
- Use pagination with `limit` and `offset`
- Consider archiving old data

## Migration from Convex

If you were previously using Convex:

1. Update `config.json` to use Supabase credentials (remove Convex settings)
2. Run the SQL schema to create tables
3. Optionally upload the format schema
4. The C++ code will automatically use Supabase REST API

The old Convex configuration keys are no longer needed:
- ~~convex_deployment_url~~
- ~~convex_mutation_endpoint~~
- ~~convex_mutation_name~~
