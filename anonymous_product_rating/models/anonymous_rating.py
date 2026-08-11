# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.tools import ormcache
import logging
import re
from datetime import datetime, timedelta
from collections import defaultdict

_logger = logging.getLogger(__name__)


class AnonymousRating(models.Model):
    _name = 'anonymous.rating'
    _description = 'Anonymous Product Rating'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # Core fields with optimized indexes
    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, 
                                     ondelete='cascade', index=True)
    rating = fields.Float(string='Rating', required=True, index=True)
    feedback = fields.Text(string='Comment')
    author_name = fields.Char(string='Name', required=True, index=True)
    author_email = fields.Char(string='Email', index=True)
    ip_address = fields.Char(string='IP Address', readonly=True, index=True)
    user_agent = fields.Text(string='User Agent', readonly=True)
    
    # Status fields with indexes for filtering
    is_published = fields.Boolean(string='Published', default=False, index=True)
    website_published = fields.Boolean(
        string='Website Published',
        related='is_published',
        store=True,
        readonly=False,
        help='Compatibility field for website.published.mixin pattern'
    )
    is_moderated = fields.Boolean(string='Moderated', default=False, readonly=True, index=True)
    moderated_by = fields.Many2one('res.users', string='Moderated By', readonly=True)
    moderation_date = fields.Datetime(string='Moderation Date', readonly=True, index=True)
    moderation_reason = fields.Text(string='Moderation Reason', readonly=True)
    recaptcha_token = fields.Char(string='reCAPTCHA Token', readonly=True)
    synced_to_core = fields.Boolean(string='Synced to Core Rating System', default=False, readonly=True, index=True,
                                   help='Indicates if this anonymous rating has been synced to rating.rating model')
    
    # Performance optimization fields
    rating_hash = fields.Char(string='Rating Hash', readonly=True, index=True,
                             help='Hash for duplicate detection and performance optimization')
    spam_score = fields.Float(string='Spam Score', default=0.0, readonly=True, index=True,
                             help='Calculated spam probability score')
    
    # Image fields for review photos
    image_1 = fields.Image(string='Review Image 1', max_width=1920, max_height=1920)
    image_2 = fields.Image(string='Review Image 2', max_width=1920, max_height=1920)
    image_3 = fields.Image(string='Review Image 3', max_width=1920, max_height=1920)
    
    # Thumbnail versions for performance
    image_1_small = fields.Image(string='Review Image 1 Small', related='image_1', max_width=256, max_height=256, store=True)
    image_2_small = fields.Image(string='Review Image 2 Small', related='image_2', max_width=256, max_height=256, store=True)
    image_3_small = fields.Image(string='Review Image 3 Small', related='image_3', max_width=256, max_height=256, store=True)
    
    # Image metadata
    has_images = fields.Boolean(string='Has Images', compute='_compute_has_images', store=True, index=True)
    image_count = fields.Integer(string='Image Count', compute='_compute_has_images', store=True)
    
    _sql_constraints = [
        ('rating_range', 'check(rating >= 1 and rating <= 5)', 'Rating must be between 1 and 5'),
        ('name_not_empty', 'check(length(trim(author_name)) > 0)', 'Name cannot be empty'),
        ('spam_score_range', 'check(spam_score >= 0 and spam_score <= 1)', 'Spam score must be between 0 and 1'),
    ]

    def init(self):
        """Create database indexes for performance optimization"""
        super().init()
        
        # Composite indexes for common queries
        tools.create_index(self._cr, 'anonymous_rating_ip_product_date_idx', 
                          self._table, ['ip_address', 'product_tmpl_id', 'create_date'])
        tools.create_index(self._cr, 'anonymous_rating_product_published_idx', 
                          self._table, ['product_tmpl_id', 'is_published'])
        tools.create_index(self._cr, 'anonymous_rating_moderation_idx', 
                          self._table, ['is_moderated', 'is_published', 'moderation_date'])
        tools.create_index(self._cr, 'anonymous_rating_spam_idx', 
                          self._table, ['spam_score', 'is_published'])
        tools.create_index(self._cr, 'anonymous_rating_hash_idx', 
                          self._table, ['rating_hash'])

    @api.depends('author_name', 'product_tmpl_id', 'rating')
    def _compute_display_name(self):
        for record in self:
            if record.product_tmpl_id and record.author_name:
                record.display_name = f"{record.author_name} - {record.product_tmpl_id.name} ({record.rating}★)"
            else:
                record.display_name = f"Rating {record.rating}★"

    @api.depends('image_1', 'image_2', 'image_3')
    def _compute_has_images(self):
        for record in self:
            images = [record.image_1, record.image_2, record.image_3]
            valid_images = [img for img in images if img]
            record.has_images = len(valid_images) > 0
            record.image_count = len(valid_images)

    @api.model_create_multi
    def create(self, vals_list):
        # Handle both single dict and list of dicts for batch creation
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        
        # Process each record in the batch with optimizations
        processed_vals_list = []
        for vals in vals_list:
            # Capture request information
            if request:
                vals['ip_address'] = request.httprequest.environ.get('REMOTE_ADDR')
                vals['user_agent'] = request.httprequest.environ.get('HTTP_USER_AGENT', '')
            
            # Sanitize input
            if 'author_name' in vals:
                vals['author_name'] = self._sanitize_text(vals['author_name'])
            if 'feedback' in vals:
                vals['feedback'] = self._sanitize_text(vals['feedback'])
            if 'author_email' in vals and vals['author_email']:
                vals['author_email'] = self._sanitize_email(vals['author_email'])
            
            # Generate rating hash for duplicate detection and performance
            vals['rating_hash'] = self._generate_rating_hash(vals)
            
            # Calculate spam score
            vals['spam_score'] = self._calculate_spam_score(vals)
            
            processed_vals_list.append(vals)
        
        # Create records
        records = super().create(processed_vals_list)
        
        # Invalidate related caches
        self._invalidate_product_caches([vals.get('product_tmpl_id') for vals in processed_vals_list])
        
        return records

    def _generate_rating_hash(self, vals):
        """Generate a hash for rating identification and duplicate detection"""
        import hashlib
        hash_string = f"{vals.get('product_tmpl_id', '')}-{vals.get('ip_address', '')}-{vals.get('author_name', '')}-{vals.get('rating', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()

    def _calculate_spam_score(self, vals):
        """Calculate spam probability score (0.0 = not spam, 1.0 = definitely spam)"""
        score = 0.0
        feedback = vals.get('feedback', '') or ''
        author_name = vals.get('author_name', '') or ''
        
        # URL detection
        if re.search(r'http[s]?://', feedback, re.IGNORECASE):
            score += 0.3
        if re.search(r'www\.', feedback, re.IGNORECASE):
            score += 0.2
        
        # Excessive caps
        if len(feedback) > 10:
            caps_ratio = sum(1 for c in feedback if c.isupper()) / len(feedback)
            if caps_ratio > 0.7:
                score += 0.4
        
        # Repeated characters
        if re.search(r'(.)\1{4,}', feedback):
            score += 0.2
        
        # Spam keywords
        spam_keywords = ['buy', 'sale', 'discount', 'offer', 'deal', 'cheap', 'free', 'win', 'prize']
        text_lower = f"{feedback} {author_name}".lower()
        keyword_count = sum(1 for keyword in spam_keywords if keyword in text_lower)
        score += min(keyword_count * 0.1, 0.3)
        
        # Email in feedback (suspicious)
        if re.search(r'@\w+\.', feedback):
            score += 0.3
        
        return min(score, 1.0)

    def _sanitize_text(self, text):
        """Sanitize text input to prevent XSS and other attacks"""
        if not text:
            return text
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', str(text))
        # Remove script tags content
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove javascript: links
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        # Limit length
        text = text[:1000] if len(text) > 1000 else text
        # Strip whitespace
        text = text.strip()
        
        return text

    def _sanitize_email(self, email):
        """Validate and sanitize email"""
        if not email:
            return email
        
        email = email.strip().lower()
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError(_('Invalid email format'))
        
        return email

    def _invalidate_product_caches(self, product_ids):
        """Invalidate product-related caches when ratings change with serialization protection"""
        if not product_ids:
            return
        
        # Skip cache invalidation during snippet processing to prevent serialization conflicts
        if self.env.context.get('snippet_processing') or self.env.context.get('tracking_disable'):
            _logger.debug("Skipping cache invalidation during snippet processing")
            return
        
        # Clear ormcache for affected products
        product_ids = [pid for pid in product_ids if pid]
        if product_ids:
            try:
                products = self.env['product.template'].browse(product_ids)
                products.invalidate_recordset(['anonymous_rating_count', 'anonymous_rating_avg', 
                                             'total_rating_count', 'total_rating_avg'])
                
                # Clear method caches
                self.env.registry.clear_cache()
            except Exception as e:
                from psycopg2 import OperationalError
                if isinstance(e, OperationalError) and 'could not serialize access' in str(e):
                    _logger.warning(f"Serialization conflict during cache invalidation, skipping")
                else:
                    _logger.error(f"Error invalidating product caches: {e}")

    def _get_cached_rate_limit_count(self, ip_address, product_id, rate_limit_hours):
        """Rate limit check — direct query (no ormcache, time-dependent)"""
        since_date = datetime.now() - timedelta(hours=rate_limit_hours)
        return self.search_count([
            ('ip_address', '=', ip_address),
            ('product_tmpl_id', '=', product_id),
            ('create_date', '>=', since_date)
        ])

    @api.model
    def check_rate_limit(self, ip_address, product_id):
        """Check if IP has exceeded rate limit for this product - optimized version"""
        if not ip_address:
            return True
            
        rate_limit_hours = int(self.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.rate_limit_hours', 24))
        max_ratings_per_period = int(self.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.max_ratings_per_period', 3))
        
        existing_count = self._get_cached_rate_limit_count(ip_address, product_id, rate_limit_hours)
        return existing_count < max_ratings_per_period

    @api.model
    def check_comprehensive_rate_limit(self, ip_address, product_id, author_name, author_email):
        """Enhanced rate limiting with multiple criteria - optimized"""
        if not self.check_rate_limit(ip_address, product_id):
            return False

        # Name-based rate limiting (cached)
        if author_name:
            name_count = self._get_cached_name_limit_count(author_name)
            if name_count >= 3:  # Max 3 per hour
                return False

        # Email-based rate limiting (cached)
        if author_email:
            email_count = self._get_cached_email_limit_count(author_email)
            if email_count >= 2:  # Max 2 per 6 hours
                return False

        return True

    def _get_cached_name_limit_count(self, author_name):
        """Name-based rate limit check — direct query (no ormcache, time-dependent)"""
        since_date = datetime.now() - timedelta(hours=1)
        return self.search_count([
            ('author_name', '=ilike', author_name),
            ('create_date', '>=', since_date)
        ])

    def _get_cached_email_limit_count(self, author_email):
        """Email-based rate limit check — direct query (no ormcache, time-dependent)"""
        since_date = datetime.now() - timedelta(hours=6)
        return self.search_count([
            ('author_email', '=', author_email),
            ('create_date', '>=', since_date)
        ])

    def action_publish(self):
        """Publish the rating and integrate with core rating system"""
        self.ensure_one()
        self.write({
            'is_published': True,
            'is_moderated': True,
            'moderated_by': self.env.user.id,
            'moderation_date': fields.Datetime.now()
        })
        
        # Note: Sync to core rating system is disabled to prevent double counting
        # Anonymous ratings are counted separately via computed fields
        
        # Invalidate caches
        self._invalidate_product_caches([self.product_tmpl_id.id])

    def action_unpublish(self):
        """Unpublish the rating and remove from core rating system"""
        self.ensure_one()
        self.write({
            'is_published': False,
            'is_moderated': True,
            'moderated_by': self.env.user.id,
            'moderation_date': fields.Datetime.now()
        })
        
        # Invalidate caches
        self._invalidate_product_caches([self.product_tmpl_id.id])

    def action_moderate(self, reason=None):
        """Mark as moderated with reason"""
        self.ensure_one()
        self.write({
            'is_moderated': True,
            'moderated_by': self.env.user.id,
            'moderation_date': fields.Datetime.now(),
            'moderation_reason': reason or ''
        })

    def action_bulk_publish(self):
        """Bulk publish multiple ratings - optimized for performance"""
        if not self:
            return
            
        # Group by product for efficient cache invalidation
        product_ids = list(set(self.mapped('product_tmpl_id.id')))
        
        # Bulk update
        self.write({
            'is_published': True,
            'is_moderated': True,
            'moderated_by': self.env.user.id,
            'moderation_date': fields.Datetime.now()
        })
        
        # Note: Sync to core rating system is disabled to prevent double counting
        # Anonymous ratings are counted separately via computed fields
        
        # Invalidate caches
        self._invalidate_product_caches(product_ids)

    def action_bulk_unpublish(self):
        """Bulk unpublish multiple ratings - optimized for performance"""
        if not self:
            return
            
        product_ids = list(set(self.mapped('product_tmpl_id.id')))
        
        self.write({
            'is_published': False,
            'is_moderated': True,
            'moderated_by': self.env.user.id,
            'moderation_date': fields.Datetime.now()
        })
        
        # Invalidate caches
        self._invalidate_product_caches(product_ids)

    @api.model
    def get_ratings_for_product(self, product_id, limit=10, offset=0, published_only=True):
        """Optimized method to get ratings for a product with pagination including images"""
        domain = [('product_tmpl_id', '=', product_id)]
        if published_only:
            domain.append(('is_published', '=', True))
        
        # Use read() for better performance when we don't need full records
        ratings = self.search(domain, limit=limit, offset=offset, order='create_date desc')
        
        # Include image data in the response
        fields_to_read = [
            'id', 'rating', 'feedback', 'author_name', 'create_date',
            'has_images', 'image_count', 'image_1_small', 'image_2_small', 'image_3_small'
        ]
        
        return ratings.read(fields_to_read)

    @api.model
    def get_rating_statistics(self, product_ids):
        """Get rating statistics for multiple products efficiently"""
        if not product_ids:
            return {}
        
        # Use raw SQL for better performance
        query = """
            SELECT 
                product_tmpl_id,
                COUNT(*) as count,
                AVG(rating) as avg_rating,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating
            FROM anonymous_rating 
            WHERE product_tmpl_id = ANY(%s) AND is_published = true
            GROUP BY product_tmpl_id
        """
        
        self.env.cr.execute(query, (product_ids,))
        results = self.env.cr.dictfetchall()
        
        # Convert to dict with product_id as key
        stats = {}
        for result in results:
            stats[result['product_tmpl_id']] = {
                'count': result['count'],
                'avg_rating': float(result['avg_rating']) if result['avg_rating'] else 0.0,
                'min_rating': float(result['min_rating']) if result['min_rating'] else 0.0,
                'max_rating': float(result['max_rating']) if result['max_rating'] else 0.0,
            }
        
        return stats

    @api.model
    def cleanup_old_ratings(self, days=365):
        """Cleanup old unpublished ratings for performance"""
        cutoff_date = datetime.now() - timedelta(days=days)
        old_ratings = self.search([
            ('create_date', '<', cutoff_date),
            ('is_published', '=', False)
        ])
        
        if old_ratings:
            _logger.info(f"Cleaning up {len(old_ratings)} old unpublished ratings")
            old_ratings.unlink()
        
        return len(old_ratings)

    @api.model
    def auto_moderate_by_spam_score(self, threshold=0.7):
        """Auto-moderate ratings based on spam score"""
        spam_ratings = self.search([
            ('spam_score', '>=', threshold),
            ('is_moderated', '=', False)
        ])
        
        if spam_ratings:
            spam_ratings.write({
                'is_moderated': True,
                'is_published': False,
                'moderation_reason': f'Auto-moderated: High spam score ({threshold})',
                'moderation_date': fields.Datetime.now()
            })
            
            _logger.info(f"Auto-moderated {len(spam_ratings)} ratings with high spam scores")
        
        return len(spam_ratings)

    @api.model
    def cron_clear_caches(self):
        """Cron job method to clear caches"""
        try:
            # Clear ORM caches
            self.env.registry.clear_cache()
            
            # Invalidate product rating computations
            products = self.env['product.template'].search([])
            products.invalidate_recordset(['anonymous_rating_count', 'anonymous_rating_avg', 
                                         'total_rating_count', 'total_rating_avg'])
            
            _logger.info("Anonymous rating caches cleared successfully")
            return True
        except Exception as e:
            _logger.error(f"Error clearing caches: {e}")
            return False

    @api.model
    def cron_sync_ratings_to_core(self):
        """Cron job method to sync ratings to core system"""
        try:
            # Find products with unsynced anonymous ratings
            products_to_sync = self.env['product.template'].search([
                ('anonymous_rating_ids.is_published', '=', True),
                ('anonymous_rating_ids.synced_to_core', '=', False)
            ])
            
            # Sync each product
            synced_count = 0
            for product in products_to_sync:
                try:
                    product.sync_anonymous_ratings_to_core()
                    synced_count += 1
                except Exception as e:
                    _logger.error(f"Failed to sync ratings for product {product.id}: {e}")
            
            _logger.info(f"Synced anonymous ratings for {synced_count} products")
            return synced_count
        except Exception as e:
            _logger.error(f"Error in sync cron job: {e}")
            return 0

    @api.model
    def cron_serialization_recovery(self):
        """Cron job method to recover from serialization failures"""
        try:
            # Force recomputation of all product ratings that might have failed
            products_with_ratings = self.env['product.template'].search([
                '|',
                ('rating_ids', '!=', False),
                ('anonymous_rating_ids', '!=', False)
            ])
            
            recovery_count = 0
            for product in products_with_ratings:
                try:
                    # Use safe context to prevent new serialization conflicts
                    safe_context = dict(self.env.context, tracking_disable=True)
                    product_safe = product.with_context(safe_context)
                    
                    # Force recomputation
                    if product_safe.force_rating_recomputation():
                        recovery_count += 1
                except Exception as e:
                    from psycopg2 import OperationalError
                    if isinstance(e, OperationalError) and 'could not serialize access' in str(e):
                        _logger.debug(f"Serialization conflict during recovery for product {product.id}, will retry later")
                    else:
                        _logger.error(f"Error during serialization recovery for product {product.id}: {e}")
            
            # Also call the product template's refresh method
            try:
                template_recovery_count = self.env['product.template'].refresh_all_rating_counts()
                _logger.info(f"Product template refresh completed for {template_recovery_count} products")
                recovery_count += template_recovery_count
            except Exception as e:
                _logger.error(f"Error in product template refresh: {e}")
            
            _logger.info(f"Serialization recovery completed for {recovery_count} products")
            return recovery_count
        except Exception as e:
            _logger.error(f"Error in serialization recovery cron job: {e}")
            return 0

    @api.model
    def check_serialization_health(self):
        """Check the health of rating computations and detect potential serialization issues"""
        try:
            # Check for products with inconsistent rating data
            products = self.env['product.template'].search([
                '|',
                ('rating_ids', '!=', False),
                ('anonymous_rating_ids', '!=', False)
            ])
            
            issues_found = 0
            for product in products:
                try:
                    # Check if computed fields are consistent
                    expected_count = len(product.rating_ids.filtered(lambda r: r.rating >= 1 and r.consumed and r.partner_id))
                    expected_count += len(product.anonymous_rating_ids.filtered('is_published'))
                    
                    if product.rating_count != expected_count:
                        _logger.warning(f"Rating count inconsistency for product {product.id}: computed={product.rating_count}, expected={expected_count}")
                        issues_found += 1
                        
                        # Try to fix the issue
                        product.force_rating_recomputation()
                        
                except Exception as e:
                    _logger.error(f"Error checking product {product.id}: {e}")
                    issues_found += 1
            
            _logger.info(f"Serialization health check completed, found {issues_found} issues")
            return issues_found
        except Exception as e:
            _logger.error(f"Error in serialization health check: {e}")
            return -1