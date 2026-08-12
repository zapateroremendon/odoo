# Anonymous Product Rating for Odoo 17

A comprehensive module that allows anonymous (non-logged) users to rate and comment on products in the Odoo website while maintaining robust security against bots and web attacks.

**Note**: This module is specifically designed for anonymous users only. Logged-in users should use Odoo's built-in rating system.

## 🌟 Features

### Core Functionality
- **Anonymous Rating System**: Users can rate products without creating accounts
- **Seamless Integration**: Works with Odoo's default rating templates and system
- **Dual Rating Display**: Combines anonymous and registered user ratings
- **Flexible Moderation**: Auto-publish or manual moderation options

### Security & Protection
- **reCAPTCHA v3 Integration**: Advanced bot protection with score-based validation
- **Multi-layer Rate Limiting**: IP, name, and email-based restrictions
- **Spam Detection**: Pattern-based content analysis
- **XSS Protection**: Content sanitization and HTML escaping
- **Request Validation**: Timestamp validation and replay attack prevention
- **User Agent Filtering**: Bot detection and blocking

### User Experience
- **Responsive Design**: Mobile-friendly rating interface
- **Real-time Validation**: Instant feedback on form submission
- **Progressive Loading**: Paginated rating display
- **Review Images**: Visitors can attach up to 3 images to their review, with automatic thumbnail generation
- **Accessibility**: WCAG compliant interface elements

## 🔧 Installation

1. **Copy Module**: Place in your Odoo addons directory
2. **Update Apps**: Refresh the app list in Odoo
3. **Install**: Install "Anonymous Product Rating" module
4. **Dependencies**: Ensure required modules are installed:
   - `website_sale`
   - `portal_rating` 
   - `rating`
   - `google_recaptcha`

## ⚙️ Configuration

### Basic Setup
Navigate to **Website > Configuration > Settings**:

- **Auto-publish**: Enable/disable automatic rating publication
- **Rate Limiting**: Configure submission limits per time period
- **Moderation**: Set content review requirements

### reCAPTCHA Configuration
1. Get reCAPTCHA v3 keys from Google
2. Configure in **Settings > General Settings > reCAPTCHA**:
   - Site Key (public)
   - Secret Key (private)
   - Minimum Score (0.0-1.0, recommended: 0.5)

### Advanced Settings
Available via **Settings > Technical > Parameters**:

```
anonymous_product_rating.auto_publish = True/False
anonymous_product_rating.rate_limit_hours = 24
anonymous_product_rating.max_ratings_per_period = 3
anonymous_product_rating.recaptcha_min_score = 0.5
anonymous_product_rating.enable_moderation = True
```

## 🚀 Usage

### For Customers
1. **Browse Products**: Navigate to any product page
2. **Rate & Review**: Click "Write a Review" button
3. **Fill Form**: Provide rating, name, and optional comment
4. **Submit**: Complete reCAPTCHA and submit

### For Administrators
1. **View Ratings**: Access via **Website > Anonymous Ratings**
2. **Moderate Content**: Approve, reject, or edit submissions
3. **Monitor Activity**: Track IP addresses and submission patterns
4. **Bulk Actions**: Mass approve/reject ratings

## 🔒 Security Features

### Bot Protection
- **reCAPTCHA v3**: Score-based human verification
- **User Agent Analysis**: Automatic bot detection
- **Request Pattern Analysis**: Suspicious behavior identification

### Rate Limiting
- **IP-based**: Limit submissions per IP address
- **Name-based**: Prevent same-name spam (3/hour)
- **Email-based**: Restrict email reuse (2/6 hours)
- **Time-based**: Minimum interval between requests

### Content Security
- **XSS Prevention**: HTML tag removal and escaping
- **Script Injection**: JavaScript code filtering
- **Content Length**: Maximum character limits
- **Spam Detection**: Pattern-based content analysis

### Request Security
- **CSRF Protection**: Built-in Odoo CSRF handling
- **Timestamp Validation**: Replay attack prevention
- **Header Validation**: Required header checking
- **Input Sanitization**: Comprehensive data cleaning

## 🎨 Customization

### Templates
The module integrates with existing Odoo templates:
- Extends `website_sale.product_comment` for seamless integration
- Provides fallback standalone template
- Customizable rating display and form elements

### Styling
CSS classes available for customization:
- `.anonymous-rating-section`: Main container
- `.rating-input`: Star rating interface
- `.rating-item`: Individual rating display
- `.rating-summary`: Statistics display

### JavaScript Events
Available events for custom functionality:
- `rating:submitted`: After successful submission
- `rating:loaded`: After ratings are loaded
- `rating:error`: On submission errors

## 📊 Database Schema

### Anonymous Rating Model (`anonymous.rating`)
- `product_tmpl_id`: Link to product
- `rating`: Float (1.0-5.0)
- `feedback`: Text comment
- `author_name`: Reviewer name
- `author_email`: Optional email
- `ip_address`: Submitter IP
- `is_published`: Publication status
- `is_moderated`: Moderation status

### Integration with Rating System
- Automatic `rating.rating` record creation
- Combined statistics calculation
- Unified display in product pages

## 🔍 Monitoring & Analytics

### Logging
The module provides comprehensive logging:
- Successful submissions
- Security violations
- Spam detection
- Rate limit violations

### Metrics Available
- Total anonymous ratings
- Publication rates
- Moderation statistics
- Security incident counts

## 🛠️ Troubleshooting

### Common Issues

**reCAPTCHA Not Working**
- Verify site/secret keys are correct
- Check domain configuration in Google Console
- Ensure HTTPS is enabled for production

**Ratings Not Appearing**
- Check if auto-publish is enabled
- Verify moderation settings
- Ensure product allows anonymous ratings

**Rate Limiting Too Strict**
- Adjust parameters in system settings
- Consider IP forwarding in proxy setups
- Review time period configurations

### Debug Mode
Enable debug logging by setting log level to DEBUG for:
- `addons.anonymous_product_rating.controllers.main`
- `addons.anonymous_product_rating.models.anonymous_rating`

## 🤝 Contributing

### Development Setup
1. Clone/fork the repository
2. Create feature branch
3. Follow Odoo development guidelines
4. Add tests for new features
5. Submit pull request

### Code Standards
- Follow PEP 8 for Python code
- Use ESLint for JavaScript
- Maintain backward compatibility
- Document all public methods

## 📄 License

This module is licensed under LGPL-3. See LICENSE file for details.

## 🆘 Support

For support and questions:
- Create issues on the repository
- Check existing documentation
- Review Odoo community forums

## 🔄 Changelog

### Version 17.0.1.0.0
- Initial release for Odoo 17
- Complete security implementation
- Integration with default rating system
- Comprehensive bot protection
- Multi-layer rate limiting
- Advanced spam detection