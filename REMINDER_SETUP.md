# Reminder System Setup on DigitalOcean Droplet

This guide walks you through setting up the automated reminder generation on your DigitalOcean droplet.

## Prerequisites

- Your Django app is deployed and running in Docker container `mulai_web`
- SSH access to your DigitalOcean droplet
- The reminder system is already deployed via your CI/CD pipeline

## Step 1: Copy the Script to Your Droplet

```bash
# From your local machine, copy the script to the droplet
scp generate_daily_reminders.sh root@YOUR_DROPLET_IP:/root/mulai_web/

# SSH into your droplet
ssh root@YOUR_DROPLET_IP
```

## Step 2: Make the Script Executable

```bash
cd /root/mulai_web
chmod +x generate_daily_reminders.sh
```

## Step 3: Test with Dry Run

```bash
# Test the script in dry-run mode first
./generate_daily_reminders.sh --dry-run
```

**Expected output:**
```
2025-07-26 14:30:00: Starting reminder generation (DRY RUN)
2025-07-26 14:30:00: Running in dry-run mode...
DRY RUN MODE - No changes will be made
Auto-resolved 0 reminders
Created 2 payment reminders
Created 1 no-visit reminders
Created 0 membership expiry reminders
Reminder generation completed
2025-07-26 14:30:01: Dry run completed successfully
2025-07-26 14:30:01: Script execution finished
```

## Step 4: Test Actual Execution

```bash
# Test actual reminder generation
./generate_daily_reminders.sh
```

**Expected output:**
```
2025-07-26 14:31:00: Starting reminder generation
2025-07-26 14:31:00: Generating reminders...
Auto-resolved 1 reminders
Created 2 payment reminders
Created 1 no-visit reminders
Created 0 membership expiry reminders
Reminder generation completed
2025-07-26 14:31:01: Reminder generation completed successfully
2025-07-26 14:31:01: Script execution finished
```

## Step 5: Set Up Cron Job

```bash
# Edit the crontab
crontab -e
```

Add this line to run the script daily at 6:00 AM server time:
```bash
0 6 * * * /root/mulai_web/generate_daily_reminders.sh >/dev/null 2>&1
```

**Alternative schedules:**
```bash
# Every day at 8:00 AM
0 8 * * * /root/mulai_web/generate_daily_reminders.sh >/dev/null 2>&1

# Every day at 6:00 AM and 6:00 PM
0 6,18 * * * /root/mulai_web/generate_daily_reminders.sh >/dev/null 2>&1

# Monday to Friday at 9:00 AM (business days only)
0 9 * * 1-5 /root/mulai_web/generate_daily_reminders.sh >/dev/null 2>&1
```

## Step 6: Verify Cron Job

```bash
# List current cron jobs
crontab -l

# Check if cron service is running
systemctl status cron
```

## Monitoring & Troubleshooting

### Check Logs
```bash
# View reminder generation logs
tail -f /root/mulai_web/reminder_generation.log

# View recent log entries
tail -20 /root/mulai_web/reminder_generation.log

# Search for errors
grep "ERROR" /root/mulai_web/reminder_generation.log
```

### Manual Testing
```bash
# Test the management command directly
docker exec mulai_web python manage.py generate_reminders --dry-run

# Check if container is running
docker ps | grep mulai_web

# View container logs if needed
docker logs mulai_web --tail 50
```

### Common Issues & Solutions

**Issue**: "Container mulai_web is not running"
```bash
# Check container status
docker ps -a | grep mulai_web

# Restart if needed (this will happen automatically on deploy)
docker start mulai_web
```

**Issue**: Permission denied
```bash
# Make sure script is executable
chmod +x /root/mulai_web/generate_daily_reminders.sh
```

**Issue**: Cron job not running
```bash
# Check cron service
systemctl status cron

# Start cron if needed
systemctl start cron

# Check system logs for cron errors
journalctl -u cron
```

## Log Rotation (Optional)

To prevent log files from growing too large:

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/reminder-generation
```

Add this content:
```
/root/mulai_web/reminder_generation.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

## Timezone Considerations

Your server timezone affects when the cron job runs:

```bash
# Check current timezone
timediff

# Change timezone if needed (example for Jakarta)
timedatectl set-timezone Asia/Jakarta
```

## Testing Different Scenarios

```bash
# Test with different member scenarios
docker exec mulai_web python manage.py shell -c "
from accounts.models import Member
from datetime import datetime, timedelta
from django.utils import timezone

# Check members who might trigger reminders
print('Members with recent payments:')
# Add your specific test queries here
"
```

## Success Indicators

✅ Script runs without errors  
✅ Log file shows successful completion  
✅ Reminders appear in Django admin  
✅ Cron job listed in `crontab -l`  
✅ Daily logs show consistent execution

## Admin Panel Access

After setup, check your admin panel:
- **Current Reminders**: `/admin/reminders/reminder/current/`
- **Reminder History**: `/admin/reminders/reminder/history/`

The reminders should appear automatically based on your member data and the business rules defined in the system. 