# Security Guide for Public Repository

## ⚠️ CRITICAL: Secrets Management

When pushing this code to a public repository, you **MUST** protect sensitive configuration data.

## What Needs Protection

### 🔴 HIGHLY SENSITIVE (Never Commit)

   - **Risk**: Anyone with this URL can read/write to your database
   - **Action**: Keep in `config.json` (already in `.gitignore`)

2. **SQL Server URL** (`config.json`)
   - Example: `live.bsr-dev.org`
   - **Risk**: Exposes internal infrastructure
   - **Action**: Keep in `config.json` (already in `.gitignore`)

### 🟡 MODERATELY SENSITIVE

3. **Log Files** (may contain telemetry data)
   - `dashboard_logs.json`
   - `telemetry_data.json`
   - `*.csv` files
   - **Action**: Already in `.gitignore`

### 🟢 SAFE TO COMMIT

4. **Private IPs** (`192.168.x.x`)
   - These are local network addresses
   - Not routable on the internet
   - Safe to include in public repos

5. **Port Numbers** (`4005`, `4003`)
   - Generic port numbers
   - Safe to commit

6. **Mutation Names** (`telemetry:storeTelemetry`)
   - API function names
   - Safe without the deployment URL

## Setup Instructions

### First Time Setup

1. **Copy the example config:**
   ```bash
   cp config.json.example config.json
   ```

2. **Edit config.json with your real values:**
   ```bash
   nano config.json  # or vim, code, etc.
   ```

   - Copy your deployment URL
   - Paste it into `config.json`

4. **Verify .gitignore is working:**
   ```bash
   git status
   # config.json should NOT appear in untracked files
   ```

### Before Committing

**ALWAYS check what you're about to commit:**

```bash
# Check staged files
git diff --cached

# Make sure config.json is NOT in the list
git status

# If config.json appears, DO NOT COMMIT
# Add it to .gitignore and try again
```

### If You Accidentally Committed Secrets

**ACT IMMEDIATELY:**

1. **Rotate all secrets:**
   - SQL: Change server URL or restrict access

2. **Remove from Git history:**
   ```bash
   # Using git-filter-repo (recommended)
   pip install git-filter-repo
   git filter-repo --path config.json --invert-paths
   
   # Force push (if already pushed to GitHub)
   git push origin --force --all
   ```

3. **Notify your team:**
   - Assume the secrets are compromised
   - Update all instances with new secrets

## Environment Variables (Alternative Approach)

For production deployments, consider using environment variables instead:

### Option 1: Shell Environment

```bash
# In ~/.bashrc or systemd service file
export SQL_SERVER_URL="your-server.example.com"
```

### Option 2: .env File (Not Implemented Yet)

```bash
# .env (add to .gitignore)
SQL_SERVER_URL=your-server.example.com

# .env.example (commit this)
SQL_SERVER_URL=your-server.example.com
```

## Verification Checklist

Before pushing to public repo:

- [ ] `config.json` is in `.gitignore`
- [ ] `config.json.example` exists with placeholder values
- [ ] No real SQL server URLs in committed files
- [ ] Log files are in `.gitignore`
- [ ] Run `git status` - no secrets listed
- [ ] Run `git diff --cached` - no secrets visible

## Security Best Practices

### 1. **Principle of Least Privilege**

### 2. **Regular Rotation**
- Change deployment URLs periodically

### 3. **Monitoring**
- Set up alerts for unusual traffic patterns

### 4. **Access Control**
- Keep the number of people with deployment URLs minimal
- Use read-only URLs for monitoring when possible

### 5. **Documentation**
- Document who has access to secrets
- Keep a log of secret rotations

## What to Do If Secrets Are Leaked

1. **Immediate Actions:**
   - Rotate all affected secrets
   - Assess what data might have been accessed

2. **Short-term:**
   - Implement IP whitelisting if available
   - Monitor for suspicious activity

3. **Long-term:**
   - Review access control policies
   - Implement automated secret scanning
   - Consider using a secrets management service

## GitHub Security Features

Enable these on your repo:

1. **Secret Scanning** (GitHub automatically detects some secrets)
2. **Branch Protection Rules** (require reviews before merging)
3. **Dependabot** (for dependency vulnerabilities)

## Resources

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [git-filter-repo](https://github.com/newren/git-filter-repo)

## Questions?

If you're unsure whether something is safe to commit:
1. **ASK FIRST**
2. When in doubt, keep it out
3. It's easier to add something later than to remove it from history
