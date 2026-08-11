# Installation Guide - Anonymous Product Rating with Serialization Protection

## Overview

This guide covers the installation of the enhanced Anonymous Product Rating module with comprehensive serialization failure protection for Odoo 17.

## Prerequisites

- Odoo 17.0+
- PostgreSQL database
- Required dependencies:
  - `website_sale`
  - `rating`

## Installation Steps

### 1. Module Installation

1. **Copy the module** to your Odoo addons directory:
   ```bash
   cp -r anonymous_product_rating /path/to/odoo/addons/
   ```

2. **Update the app list** in Odoo:
   - Go to Apps menu
   - Click "Update Apps List"
   - Search for "Anonymous Product Rating"

3. **Install the module**:
   - Click "Install" on the Anonymous Product Rating module
   - Wait for installation to complete

### 2. Post-Installation Configuration

The module includes an automatic post-installation hook that:
- Enables the serialization recovery cron job
- Runs an initial health check
- Sets up the protection mechanisms

### 3. Verification

After installation, verify the setup:

1. **Check Cron Jobs**:
   - Go to Settings > Technical > Automation > Scheduled Actions
   - Look for "Anonymous Rating: Serialization Recovery"
   - Ensure it's active and scheduled to run hourly

2. **Test Rating Functionality**:
   - Visit a product page on your website
   - Try submitting an anonymous rating
   - Verify ratings display correctly

3. **Check Logs**:
   ```bash
   tail -f /var/log/odoo/odoo.log | grep -i "anonymous_rating"
   ```

## Configuration Options

### Cron Jobs

The module includes several cron jobs for maintenance:

1. **Serialization Recovery** (Hourly, Active):
   - Recovers from serialization failures
   - Fixes inconsistent rating data
   - Runs health checks

2. **Cache Cleanup** (Weekly, Inactive by default):
   - Clears rating caches
   - Prevents memory issues

3. **Spam Moderation** (Hourly, Inactive by default):
   - Auto-moderates high spam score ratings
   - Configurable threshold

4. **Old Rating Cleanup** (Daily, Inactive by default):
   - Removes old unpublished ratings
   - Configurable retention period

### Manual Configuration

To enable additional cron jobs:

1. Go to Settings > Technical > Automation > Scheduled Actions
2. Find the desired cron job
3. Set "Active" to True
4. Save

## Troubleshooting

### Common Issues

1. **Installation Fails with Model Reference Error**:
   - Ensure all dependencies are installed
   - Check that `website_sale` and `rating` modules are active
   - Restart Odoo service

2. **Ratings Not Displaying**:
   - Check if products have `allow_anonymous_rating` enabled
   - Verify template inheritance is working
   - Check browser console for JavaScript errors

3. **Serialization Conflicts Still Occurring**:
   - Check if cron job is active
   - Run manual recovery: `/shop/rating/serialization_recovery`
   - Check logs for specific error patterns

### Manual Recovery

If you encounter issues, you can manually trigger recovery:

1. **Via Web Interface** (Admin users):
   ```javascript
   // Open browser console and run:
   fetch('/shop/rating/serialization_recovery', {
       method: 'POST',
       headers: {'Content-Type': 'application/json'},
       body: JSON.stringify({})
   }).then(r => r.json()).then(console.log);
   ```

2. **Via Odoo Shell**:
   ```python
   # Connect to Odoo shell
   env['anonymous.rating'].cron_serialization_recovery()
   env['anonymous.rating'].check_serialization_health()
   ```

3. **Via Database**:
   ```python
   # Force recomputation for all products
   env['product.template'].refresh_all_rating_counts()
   ```

### Health Check

To check system health:

```javascript
// Browser console
fetch('/shop/rating/health_check', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({})
}).then(r => r.json()).then(console.log);
```

## Performance Monitoring

### Key Metrics to Monitor

1. **Serialization Conflicts**:
   ```bash
   grep -i "serialization conflict" /var/log/odoo/odoo.log | wc -l
   ```

2. **Recovery Operations**:
   ```bash
   grep -i "recovery completed" /var/log/odoo/odoo.log
   ```

3. **Health Issues**:
   ```bash
   grep -i "health check" /var/log/odoo/odoo.log
   ```

### Performance Optimization

1. **Database Tuning**:
   - Ensure proper PostgreSQL configuration
   - Monitor connection pool usage
   - Consider read replicas for high traffic

2. **Caching**:
   - Monitor cache hit rates
   - Adjust cache cleanup frequency if needed
   - Consider Redis for session storage

3. **Load Balancing**:
   - Use multiple Odoo instances
   - Implement sticky sessions
   - Monitor serialization conflicts across instances

## Uninstallation

To safely uninstall the module:

1. **Disable Cron Jobs**:
   - Go to Scheduled Actions
   - Deactivate all Anonymous Rating cron jobs

2. **Backup Data**:
   ```sql
   -- Backup anonymous ratings
   pg_dump -t anonymous_rating your_database > anonymous_ratings_backup.sql
   ```

3. **Uninstall Module**:
   - Go to Apps menu
   - Find Anonymous Product Rating
   - Click "Uninstall"

## Support

For issues or questions:

1. Check the logs for specific error messages
2. Run health check to identify issues
3. Use manual recovery if needed
4. Consult the SERIALIZATION_SOLUTION.md for technical details

## Version Information

- **Module Version**: 17.0.1.0.0
- **Odoo Compatibility**: 17.0+
- **Last Updated**: 2024
- **License**: LGPL-3