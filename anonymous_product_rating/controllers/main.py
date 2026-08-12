# -*- coding: utf-8 -*-

import json
import logging
import requests
import hashlib
import time
import re
from datetime import datetime, timedelta
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
from odoo.addons.website.controllers.main import Website
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class AnonymousRatingController(http.Controller):



    @http.route('/shop/product/anonymous_rating/submit', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def submit_anonymous_rating(self, **kwargs):
        """Submit an anonymous rating for a product"""
        try:
            # For JSON-RPC requests the params are injected into kwargs, but
            # some clients may send plain JSON payloads without the JSON-RPC
            # envelope. In that case, parse the raw request body and fall back
            # to its values.
            if not kwargs:
                try:
                    raw_body = request.httprequest.get_data(as_text=True)
                    parsed_body = json.loads(raw_body) if raw_body else {}
                    if isinstance(parsed_body, dict) and any(
                        key in parsed_body for key in (
                            'product_id', 'rating', 'author_name',
                            'feedback', 'author_email', 'recaptcha_token',
                            'timestamp')):
                        kwargs = parsed_body
                except ValueError:
                    pass

            # Get and validate parameters
            product_id = kwargs.get('product_id')
            rating = kwargs.get('rating')
            feedback = kwargs.get('feedback', '')
            author_name = kwargs.get('author_name', '')
            author_email = kwargs.get('author_email', '')
            recaptcha_token = kwargs.get('recaptcha_token', '')
            timestamp = kwargs.get('timestamp', '')

            # Validate required fields
            if not all([product_id, rating, author_name]):
                return {'error': _('Missing required fields')}

            # Validate timestamp to prevent replay attacks
            if timestamp and not self._validate_timestamp(timestamp):
                return {'error': _('Invalid request timestamp')}

            # Validate rating
            try:
                rating = float(rating)
                if not (1 <= rating <= 5):
                    return {'error': _('Rating must be between 1 and 5')}
            except (ValueError, TypeError):
                return {'error': _('Invalid rating value')}

            # Get product
            try:
                product_id = int(product_id)
                product = request.env['product.template'].sudo().browse(product_id)
                if not product.exists():
                    return {'error': _('Product not found')}
            except (ValueError, TypeError):
                return {'error': _('Invalid product ID')}

            if not product.allow_anonymous_rating:
                return {'error': _('Anonymous rating not allowed for this product')}

            # Check rate limiting
            ip_address = self._get_client_ip()
            rate_limit_check = self._check_comprehensive_rate_limit(ip_address, product_id, author_name, author_email)
            if not rate_limit_check:
                return {'error': _('Rate limit exceeded. Please try again later.')}

            # Verify reCAPTCHA if configured
            if not self._verify_recaptcha(recaptcha_token):
                return {'error': _('Security verification failed. Please try again.')}

            # Check for spam content
            if self._is_spam_content(feedback, author_name):
                return {'error': _('Content appears to be spam. Please review your submission.')}

            # Sanitize and validate input
            feedback = self._sanitize_content(feedback)
            author_name = self._sanitize_content(author_name)
            author_email = self._sanitize_email(author_email) if author_email else ''
            
            # Final validation to ensure author_name is not empty after sanitization
            if not author_name or not author_name.strip():
                return {'error': _('Name is required and cannot be empty')}

            # Create anonymous rating
            should_publish = self._should_auto_publish()
            anonymous_rating = request.env['anonymous.rating'].sudo().create({
                'product_tmpl_id': product.id,
                'rating': rating,
                'feedback': feedback,
                'author_name': author_name,
                'author_email': author_email,
                'recaptcha_token': recaptcha_token,
                'is_published': should_publish,
            })

            # If published, integrate with core rating system immediately
            if should_publish:
                anonymous_rating.action_publish()
            else:
                # Even if not auto-published, mark as moderated if no moderation is required
                enable_moderation = request.env['ir.config_parameter'].sudo().get_param(
                    'anonymous_product_rating.enable_moderation', 'True').lower() == 'true'
                if not enable_moderation:
                    anonymous_rating.action_publish()

            return {
                'success': True,
                'message': _('Thank you for your rating!') if anonymous_rating.is_published 
                          else _('Thank you for your rating! It will be published after moderation.')
            }

        except ValidationError as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.error("Error submitting anonymous rating: %s", str(e))
            return {'error': _('An error occurred while submitting your rating')}

    @http.route('/shop/product/anonymous_rating/submit_with_images', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def submit_anonymous_rating_with_images(self, **kwargs):
        """Submit an anonymous rating with image uploads"""
        try:
            # Get and validate parameters
            product_id = kwargs.get('product_id')
            rating = kwargs.get('rating')
            feedback = kwargs.get('feedback', '')
            author_name = kwargs.get('author_name', '')
            author_email = kwargs.get('author_email', '')
            recaptcha_token = kwargs.get('recaptcha_token', '')
            
            # Handle image uploads
            image_1 = request.httprequest.files.get('image_1')
            image_2 = request.httprequest.files.get('image_2')
            image_3 = request.httprequest.files.get('image_3')

            # Validate required fields
            if not all([product_id, rating, author_name]):
                return request.make_response(
                    json.dumps({'error': _('Missing required fields')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Validate rating
            try:
                rating = float(rating)
                if not (1 <= rating <= 5):
                    return request.make_response(
                        json.dumps({'error': _('Rating must be between 1 and 5')}),
                        headers=[('Content-Type', 'application/json')]
                    )
            except (ValueError, TypeError):
                return request.make_response(
                    json.dumps({'error': _('Invalid rating value')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Get product
            try:
                product_id = int(product_id)
                product = request.env['product.template'].sudo().browse(product_id)
                if not product.exists():
                    return request.make_response(
                        json.dumps({'error': _('Product not found')}),
                        headers=[('Content-Type', 'application/json')]
                    )
            except (ValueError, TypeError):
                return request.make_response(
                    json.dumps({'error': _('Invalid product ID')}),
                    headers=[('Content-Type', 'application/json')]
                )

            if not product.allow_anonymous_rating:
                return request.make_response(
                    json.dumps({'error': _('Anonymous rating not allowed for this product')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Check rate limiting
            ip_address = self._get_client_ip()
            rate_limit_check = self._check_comprehensive_rate_limit(ip_address, product_id, author_name, author_email)
            if not rate_limit_check:
                return request.make_response(
                    json.dumps({'error': _('Rate limit exceeded. Please try again later.')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Verify reCAPTCHA if configured
            if not self._verify_recaptcha(recaptcha_token):
                return request.make_response(
                    json.dumps({'error': _('Security verification failed. Please try again.')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Process image uploads
            image_data = {}
            for i, image_file in enumerate([image_1, image_2, image_3], 1):
                if image_file and self._validate_image(image_file):
                    try:
                        import base64
                        image_data[f'image_{i}'] = base64.b64encode(image_file.read()).decode('utf-8')
                    except Exception as e:
                        _logger.warning(f"Error processing image {i}: {str(e)}")

            # Sanitize content
            feedback = self._sanitize_content(feedback)
            author_name = self._sanitize_content(author_name)
            author_email = self._sanitize_email(author_email) if author_email else ''

            # Final validation
            if not author_name or not author_name.strip():
                return request.make_response(
                    json.dumps({'error': _('Name is required and cannot be empty')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Create anonymous rating with images
            should_publish = self._should_auto_publish()
            rating_data = {
                'product_tmpl_id': product.id,
                'rating': rating,
                'feedback': feedback,
                'author_name': author_name,
                'author_email': author_email,
                'recaptcha_token': recaptcha_token,
                'is_published': should_publish,
            }
            rating_data.update(image_data)
            
            anonymous_rating = request.env['anonymous.rating'].sudo().create(rating_data)

            # Publish if needed
            if should_publish:
                anonymous_rating.action_publish()
            else:
                enable_moderation = request.env['ir.config_parameter'].sudo().get_param(
                    'anonymous_product_rating.enable_moderation', 'True').lower() == 'true'
                if not enable_moderation:
                    anonymous_rating.action_publish()

            # Return JSON response
            response_data = {
                'success': True,
                'message': _('Thank you for your rating!') if anonymous_rating.is_published 
                          else _('Thank you for your rating! It will be published after moderation.'),
                'rating_id': anonymous_rating.id,
                'has_images': anonymous_rating.has_images,
                'image_count': anonymous_rating.image_count
            }
            
            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error("Error submitting anonymous rating with images: %s", str(e))
            return request.make_response(
                json.dumps({'error': _('An error occurred while submitting your rating')}),
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/shop/product/<int:product_id>/anonymous_ratings', type='json', auth='public', methods=['POST'], website=True)
    def get_anonymous_ratings(self, product_id, page=1, limit=10):
        """Get anonymous ratings for a product - optimized version"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return {'error': _('Product not found')}

            # Get pagination limits from configuration
            max_limit = int(request.env['ir.config_parameter'].sudo().get_param(
                'anonymous_product_rating.max_ratings_per_page', '50'))
            default_limit = int(request.env['ir.config_parameter'].sudo().get_param(
                'anonymous_product_rating.default_ratings_per_page', '10'))
            
            # Use default if no limit provided, enforce maximum
            limit = int(limit) if limit else default_limit
            limit = min(limit, max_limit)
            
            offset = (int(page) - 1) * limit

            # Use optimized method from model
            ratings_data = request.env['anonymous.rating'].sudo().get_ratings_for_product(
                product_id, limit=limit, offset=offset, published_only=True)

            # Format dates
            for rating in ratings_data:
                if rating.get('create_date'):
                    rating['create_date'] = rating['create_date'].strftime('%Y-%m-%d %H:%M:%S')

            # Get total count efficiently
            total_count = request.env['anonymous.rating'].sudo().search_count([
                ('product_tmpl_id', '=', product_id),
                ('is_published', '=', True)
            ])

            return {
                'success': True,
                'ratings': ratings_data,
                'total_count': total_count,
                'page': int(page),
                'limit': limit,
                'has_more': total_count > offset + len(ratings_data)
            }

        except Exception as e:
            _logger.error("Error getting anonymous ratings: %s", str(e))
            return {'error': _('An error occurred while loading ratings')}

    @http.route('/shop/product/<int:product_id>/anonymous_ratings_with_images', type='json', auth='public', methods=['POST'], website=True)
    def get_anonymous_ratings_with_images(self, product_id, page=1, limit=10):
        """Get anonymous ratings with full image data for display"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return {'error': _('Product not found')}

            # Get pagination limits from configuration
            max_limit = int(request.env['ir.config_parameter'].sudo().get_param(
                'anonymous_product_rating.max_ratings_per_page', '50'))
            default_limit = int(request.env['ir.config_parameter'].sudo().get_param(
                'anonymous_product_rating.default_ratings_per_page', '10'))
            
            # Use default if no limit provided, enforce maximum
            limit = int(limit) if limit else default_limit
            limit = min(limit, max_limit)
            
            offset = (int(page) - 1) * limit
            domain = [
                ('product_tmpl_id', '=', product_id),
                ('is_published', '=', True)
            ]

            # Get ratings with all image data
            ratings = request.env['anonymous.rating'].sudo().search(
                domain, limit=limit, offset=offset, order='create_date desc'
            )

            ratings_data = []
            for rating in ratings:
                rating_data = {
                    'id': rating.id,
                    'rating': rating.rating,
                    'feedback': rating.feedback,
                    'author_name': rating.author_name,
                    'create_date': rating.create_date.strftime('%Y-%m-%d %H:%M:%S') if rating.create_date else '',
                    'has_images': rating.has_images,
                    'image_count': rating.image_count,
                }
                
                # Add image data if available
                if rating.has_images:
                    if rating.image_1_small:
                        rating_data['image_1_small'] = rating.image_1_small.decode('utf-8') if isinstance(rating.image_1_small, bytes) else rating.image_1_small
                        rating_data['image_1'] = rating.image_1.decode('utf-8') if isinstance(rating.image_1, bytes) else rating.image_1
                    if rating.image_2_small:
                        rating_data['image_2_small'] = rating.image_2_small.decode('utf-8') if isinstance(rating.image_2_small, bytes) else rating.image_2_small
                        rating_data['image_2'] = rating.image_2.decode('utf-8') if isinstance(rating.image_2, bytes) else rating.image_2
                    if rating.image_3_small:
                        rating_data['image_3_small'] = rating.image_3_small.decode('utf-8') if isinstance(rating.image_3_small, bytes) else rating.image_3_small
                        rating_data['image_3'] = rating.image_3.decode('utf-8') if isinstance(rating.image_3, bytes) else rating.image_3
                
                ratings_data.append(rating_data)

            # Get total count
            total_count = request.env['anonymous.rating'].sudo().search_count(domain)

            return {
                'success': True,
                'ratings': ratings_data,
                'total_count': total_count,
                'page': int(page),
                'limit': limit,
                'has_more': total_count > offset + len(ratings_data)
            }

        except Exception as e:
            _logger.error("Error getting anonymous ratings with images: %s", str(e))
            return {'error': _('An error occurred while loading ratings')}

    @http.route('/shop/product/<int:product_id>/combined_rating_stats', type='http', auth='public', methods=['GET'], website=True)
    def get_combined_rating_stats(self, product_id):
        """Get combined rating statistics for a product (regular + anonymous)"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return request.make_response(
                    json.dumps({'error': _('Product not found')}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Get combined stats using the product method
            combined_count = product.get_combined_rating_count()
            combined_avg = product.get_combined_rating_avg()

            response_data = {
                'success': True,
                'count': combined_count,
                'avg': combined_avg,
                'product_id': product_id
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error("Error getting combined rating stats: %s", str(e))
            return request.make_response(
                json.dumps({'error': _('An error occurred while loading rating stats')}),
                headers=[('Content-Type', 'application/json')]
            )

    def _verify_recaptcha(self, token):
        """Verify reCAPTCHA token"""
        secret_key = request.env['ir.config_parameter'].sudo().get_param('anonymous_product_rating.recaptcha_secret_key')
        if not secret_key:
            return True  # Skip verification if not configured

        if not token:
            return True  # Allow if no token provided

        try:
            response = requests.post('https://www.recaptcha.net/recaptcha/api/siteverify', {
                'secret': secret_key,
                'response': token,
                'remoteip': self._get_client_ip()
            }, timeout=10)

            result = response.json()
            success = result.get('success', False)
            score = result.get('score', 0)
            
            min_score = float(request.env['ir.config_parameter'].sudo().get_param(
                'anonymous_product_rating.recaptcha_min_score', '0.5'))
            
            return success and score >= min_score

        except Exception as e:
            _logger.error("reCAPTCHA verification error: %s", str(e))
            return True  # Allow on error

    def _should_auto_publish(self):
        """Check if ratings should be auto-published based on configuration"""
        auto_publish = request.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.auto_publish', 'False').lower() == 'true'
        enable_moderation = request.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.enable_moderation', 'True').lower() == 'true'
        
        if auto_publish:
            return True
        elif not enable_moderation:
            return True
        else:
            return False

    def _get_client_ip(self):
        """Get the real client IP address"""
        forwarded_for = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.httprequest.environ.get('HTTP_X_REAL_IP')
        if real_ip:
            return real_ip
        
        return request.httprequest.environ.get('REMOTE_ADDR', '')

    def _validate_timestamp(self, timestamp):
        """Validate timestamp to prevent replay attacks"""
        if not timestamp:
            return True
        
        try:
            timestamp = float(timestamp)
            current_time = time.time()
            # Get timestamp window from configuration (in seconds)
            timestamp_window = int(request.env['ir.config_parameter'].sudo().get_param(
                'anonymous_product_rating.timestamp_validation_window', '300'))
            return abs(current_time - timestamp) <= timestamp_window
        except (ValueError, TypeError):
            return True

    def _check_comprehensive_rate_limit(self, ip_address, product_id, author_name, author_email):
        """Enhanced rate limiting with multiple criteria - optimized"""
        try:
            # Use the optimized method from the model
            return request.env['anonymous.rating'].sudo().check_comprehensive_rate_limit(
                ip_address, product_id, author_name, author_email)
        except Exception as e:
            _logger.error(f"Rate limit check error: {str(e)}")
            return False

    def _is_spam_content(self, feedback, author_name):
        """Basic spam detection"""
        if not feedback and not author_name:
            return False

        spam_patterns = [
            r'http[s]?://',
            r'www\.',
            r'@\w+\.',
            r'\b(buy|sale|discount|offer|deal|cheap|free|win|prize)\b',
            r'(.)\1{4,}',
        ]

        text_to_check = f"{feedback} {author_name}".lower()
        
        for pattern in spam_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True

        if len(feedback) > 10:
            try:
                caps_ratio = sum(1 for c in feedback if c.isupper()) / len(feedback)
                if caps_ratio > 0.7:
                    return True
            except (ZeroDivisionError, TypeError):
                # Handle edge cases where feedback might be empty or invalid
                pass

        return False

    def _sanitize_content(self, content):
        """Sanitize content to prevent XSS and other attacks"""
        if not content:
            return content or ''
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', str(content))
        # Remove script tags content
        content = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # Remove javascript: links
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        # Limit length
        content = content[:1000] if len(content) > 1000 else content
        # Strip whitespace
        content = content.strip()
        
        return content or ''

    def _sanitize_email(self, email):
        """Validate and sanitize email"""
        if not email:
            return ''
            
        email = email.strip().lower()
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return ''

        return email

    def _validate_image(self, image_file):
        """Validate uploaded image file"""
        if not image_file:
            return False
            
        # Check file size - get from configuration
        max_size_mb = float(request.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.max_image_size_mb', '5'))
        max_size = int(max_size_mb * 1024 * 1024)
        if hasattr(image_file, 'content_length') and image_file.content_length > max_size:
            return False
            
        # Check file extension - get from configuration
        allowed_extensions_param = request.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.allowed_image_extensions', '.jpg,.jpeg,.png,.gif,.webp')
        allowed_extensions = [ext.strip() for ext in allowed_extensions_param.split(',')]
        filename = getattr(image_file, 'filename', '').lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return False
            
        # Check MIME type - get from configuration
        allowed_mimes_param = request.env['ir.config_parameter'].sudo().get_param(
            'anonymous_product_rating.allowed_image_mimes', 'image/jpeg,image/png,image/gif,image/webp')
        allowed_mimes = [mime.strip() for mime in allowed_mimes_param.split(',')]
        content_type = getattr(image_file, 'content_type', '').lower()
        if content_type and content_type not in allowed_mimes:
            return False
            
        return True

    @http.route('/shop/rating/serialization_recovery', type='json', auth='user', methods=['POST'])
    def trigger_serialization_recovery(self, **kwargs):
        """Manual trigger for serialization recovery (admin only)"""
        try:
            # Check if user has admin rights
            if not request.env.user.has_group('base.group_system'):
                return {'error': _('Access denied. Admin rights required.')}
            
            # Trigger recovery
            recovery_count = request.env['anonymous.rating'].sudo().cron_serialization_recovery()
            health_issues = request.env['anonymous.rating'].sudo().check_serialization_health()
            
            return {
                'success': True,
                'message': f'Serialization recovery completed. Recovered {recovery_count} products, found {health_issues} health issues.',
                'recovery_count': recovery_count,
                'health_issues': health_issues
            }
        except Exception as e:
            _logger.error(f"Error in manual serialization recovery: {e}")
            return {'error': _('Recovery failed: ') + str(e)}

    @http.route('/shop/rating/health_check', type='json', auth='user', methods=['GET', 'POST'])
    def rating_health_check(self, **kwargs):
        """Check rating system health (admin only)"""
        try:
            # Check if user has admin rights
            if not request.env.user.has_group('base.group_system'):
                return {'error': _('Access denied. Admin rights required.')}
            
            # Run health check
            health_issues = request.env['anonymous.rating'].sudo().check_serialization_health()
            
            # Get some statistics
            total_products = request.env['product.template'].sudo().search_count([
                '|',
                ('rating_ids', '!=', False),
                ('anonymous_rating_ids', '!=', False)
            ])
            
            total_anonymous_ratings = request.env['anonymous.rating'].sudo().search_count([])
            published_anonymous_ratings = request.env['anonymous.rating'].sudo().search_count([('is_published', '=', True)])
            
            return {
                'success': True,
                'health_issues': health_issues,
                'statistics': {
                    'total_products_with_ratings': total_products,
                    'total_anonymous_ratings': total_anonymous_ratings,
                    'published_anonymous_ratings': published_anonymous_ratings,
                }
            }
        except Exception as e:
            _logger.error(f"Error in rating health check: {e}")
            return {'error': _('Health check failed: ') + str(e)}