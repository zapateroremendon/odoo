/** @odoo-module **/

import { Component, onMounted, useRef } from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.AnonymousRatingWithImages = publicWidget.Widget.extend({
    selector: '.anonymous-rating-form',
    events: {
        'change input[type="file"]': '_onImageChange',
        'click .remove-image': '_onRemoveImage',
        'click .rating-star': '_onRatingClick',
        'submit #anonymousRatingForm': '_onFormSubmit',
        'click .rating-image-thumb': '_onImageClick',
        'input #feedback': '_onFeedbackInput',
        'click #loadMoreBtn': '_onLoadMore',
    },

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initializeRatingStars();
        this._initializeImagePreviews();
        this._initializeCharacterCounter();
        this._loadInitialRatings();
        this.currentPage = 1;
        this.hasMore = true;
    },

    /**
     * Initialize rating stars functionality
     */
    _initializeRatingStars: function () {
        const stars = this.$('.rating-star');
        const ratingInput = this.$('#ratingValue');
        
        stars.on('mouseenter', function () {
            const rating = $(this).data('rating');
            stars.each(function (index) {
                if (index < rating) {
                    $(this).removeClass('fa-star-o').addClass('fa-star');
                } else {
                    $(this).removeClass('fa-star').addClass('fa-star-o');
                }
            });
        });
        
        this.$('.rating-input').on('mouseleave', function () {
            const currentRating = ratingInput.val();
            stars.each(function (index) {
                if (index < currentRating) {
                    $(this).removeClass('fa-star-o').addClass('fa-star');
                } else {
                    $(this).removeClass('fa-star').addClass('fa-star-o');
                }
            });
        });
    },

    /**
     * Initialize image preview functionality
     */
    _initializeImagePreviews: function () {
        const self = this;
        this.$('input[type="file"]').each(function () {
            const input = $(this);
            const previewId = input.attr('id').replace('image', 'preview');
            const preview = self.$('#' + previewId);
            
            // Clear any existing preview
            preview.empty();
        });
    },

    /**
     * Handle rating star click
     */
    _onRatingClick: function (ev) {
        const rating = $(ev.currentTarget).data('rating');
        this.$('#ratingValue').val(rating);
        
        // Update visual state
        this.$('.rating-star').each(function (index) {
            if (index < rating) {
                $(this).removeClass('fa-star-o').addClass('fa-star active');
            } else {
                $(this).removeClass('fa-star active').addClass('fa-star-o');
            }
        });
    },

    /**
     * Handle image file selection
     */
    _onImageChange: function (ev) {
        const input = ev.currentTarget;
        const file = input.files[0];
        const previewId = input.id.replace('image', 'preview');
        const preview = this.$('#' + previewId);
        const uploadBox = $(input).closest('.image-upload-box');
        
        if (file) {
            // Validate file
            if (!this._validateImageFile(file)) {
                this._showImageError(uploadBox, 'Invalid file. Please select a valid image (JPG, PNG, GIF, WebP) under 5MB.');
                input.value = '';
                return;
            }
            
            // Show preview
            const reader = new FileReader();
            reader.onload = function (e) {
                preview.html(`
                    <img src="${e.target.result}" alt="Preview">
                    <button type="button" class="remove-image" title="Remove image">
                        <i class="fa fa-times"></i>
                    </button>
                `);
                uploadBox.addClass('has-image');
            };
            reader.readAsDataURL(file);
        } else {
            // Clear preview
            preview.empty();
            uploadBox.removeClass('has-image');
        }
    },

    /**
     * Handle image removal
     */
    _onRemoveImage: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        const removeBtn = $(ev.currentTarget);
        const preview = removeBtn.closest('.image-preview');
        const uploadBox = removeBtn.closest('.image-upload-box');
        const input = uploadBox.find('input[type="file"]');
        
        // Clear input and preview
        input.val('');
        preview.empty();
        uploadBox.removeClass('has-image');
    },

    /**
     * Handle form submission
     */
    _onFormSubmit: function (ev) {
        ev.preventDefault();
        
        const form = $(ev.currentTarget);
        const submitBtn = form.find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        // Validate form
        if (!this._validateForm(form)) {
            return;
        }
        
        // Show loading state
        submitBtn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Submitting...');
        form.addClass('image-uploading');
        
        // Prepare form data
        const formData = new FormData(form[0]);
        
        // Submit via AJAX
        $.ajax({
            url: '/shop/product/anonymous_rating/submit_with_images',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: (response) => {
                this._handleSubmitSuccess(response, form, submitBtn, originalText);
            },
            error: (xhr, status, error) => {
                this._handleSubmitError(xhr, form, submitBtn, originalText);
            }
        });
    },

    /**
     * Handle successful form submission
     */
    _handleSubmitSuccess: function (response, form, submitBtn, originalText) {
        form.removeClass('image-uploading');
        submitBtn.prop('disabled', false).html(originalText);
        
        try {
            const data = typeof response === 'string' ? JSON.parse(response) : response;
            
            if (data.success) {
                // Show success message
                this._showSuccessMessage(data.message);
                
                // Reset form
                form[0].reset();
                this._resetForm();
                
                // Refresh ratings display
                const productId = form.find('input[name="product_id"]').val();
                if (productId) {
                    this._loadRatings(productId, 1);
                }
            } else {
                this._showErrorMessage(data.error || 'An error occurred while submitting your rating.');
            }
        } catch (e) {
            this._showErrorMessage('An error occurred while processing the response.');
        }
    },

    /**
     * Handle form submission error
     */
    _handleSubmitError: function (xhr, form, submitBtn, originalText) {
        form.removeClass('image-uploading');
        submitBtn.prop('disabled', false).html(originalText);
        
        let errorMessage = 'An error occurred while submitting your rating.';
        
        try {
            const response = JSON.parse(xhr.responseText);
            if (response.error) {
                errorMessage = response.error;
            }
        } catch (e) {
            // Use default error message
        }
        
        this._showErrorMessage(errorMessage);
    },

    /**
     * Handle image thumbnail click for modal display
     */
    _onImageClick: function (ev) {
        const img = $(ev.currentTarget);
        const fullImageSrc = img.data('full-image') || img.attr('src');
        const alt = img.attr('alt');
        
        // Update modal content
        $('#modalImage').attr('src', fullImageSrc).attr('alt', alt);
        $('#imageModalLabel').text(alt);
    },

    /**
     * Validate image file
     */
    _validateImageFile: function (file) {
        // Check file size (5MB max)
        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            return false;
        }
        
        // Check file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            return false;
        }
        
        return true;
    },

    /**
     * Validate form before submission
     */
    _validateForm: function (form) {
        const rating = form.find('#ratingValue').val();
        const authorName = form.find('#authorName').val().trim();
        
        if (!rating || rating < 1 || rating > 5) {
            this._showErrorMessage('Please select a rating.');
            return false;
        }
        
        if (!authorName) {
            this._showErrorMessage('Please enter your name.');
            form.find('#authorName').focus();
            return false;
        }
        
        return true;
    },

    /**
     * Reset form to initial state
     */
    _resetForm: function () {
        // Reset rating stars
        this.$('.rating-star').removeClass('fa-star active').addClass('fa-star-o');
        this.$('#ratingValue').val('');
        
        // Reset image previews
        this.$('.image-preview').empty();
        this.$('.image-upload-box').removeClass('has-image');
    },

    /**
     * Show image error
     */
    _showImageError: function (uploadBox, message) {
        uploadBox.addClass('image-upload-error');
        this._showErrorMessage(message);
        
        setTimeout(() => {
            uploadBox.removeClass('image-upload-error');
        }, 3000);
    },

    /**
     * Show success message
     */
    _showSuccessMessage: function (message) {
        this._showMessage(message, 'success');
    },

    /**
     * Show error message
     */
    _showErrorMessage: function (message) {
        this._showMessage(message, 'danger');
    },

    /**
     * Initialize character counter for feedback
     */
    _initializeCharacterCounter: function () {
        const feedback = this.$('#feedback');
        const charCount = this.$('#charCount');
        
        if (feedback.length && charCount.length) {
            feedback.on('input', () => {
                const count = feedback.val().length;
                charCount.text(count);
                
                if (count > 900) {
                    charCount.addClass('text-warning');
                } else if (count > 950) {
                    charCount.addClass('text-danger').removeClass('text-warning');
                } else {
                    charCount.removeClass('text-warning text-danger');
                }
            });
        }
    },

    /**
     * Load initial ratings
     */
    _loadInitialRatings: function () {
        const productId = this.$('input[name="product_id"]').val();
        if (!productId) return;
        
        this._loadRatings(productId, 1);
    },

    /**
     * Load ratings with images
     */
    _loadRatings: function (productId, page = 1) {
        const container = $('#ratingsContainer');
        const loadMoreContainer = $('#loadMoreContainer');
        
        if (page === 1) {
            container.html('<div class="text-center"><i class="fa fa-spinner fa-spin"></i> Loading reviews...</div>');
        }
        
        $.ajax({
            url: `/shop/product/${productId}/anonymous_ratings_with_images`,
            type: 'POST',
            data: JSON.stringify({ page: page, limit: 5 }),
            contentType: 'application/json',
            success: (response) => {
                if (response.success) {
                    if (page === 1) {
                        container.empty();
                    }
                    
                    if (response.ratings.length > 0) {
                        response.ratings.forEach(rating => {
                            container.append(this._renderRating(rating));
                        });
                        
                        this.hasMore = response.has_more;
                        this.currentPage = page;
                        
                        if (this.hasMore) {
                            loadMoreContainer.show();
                        } else {
                            loadMoreContainer.hide();
                        }
                    } else if (page === 1) {
                        container.html(`
                            <div class="text-center text-muted py-4">
                                <i class="fa fa-comment-o fa-3x mb-3"></i>
                                <p>No reviews yet. Be the first to review this product!</p>
                            </div>
                        `);
                    }
                } else {
                    this._showErrorMessage(response.error || 'Failed to load reviews');
                }
            },
            error: () => {
                this._showErrorMessage('Failed to load reviews');
            }
        });
    },

    /**
     * Render a single rating
     */
    _renderRating: function (rating) {
        const stars = this._renderStars(rating.rating);
        const images = this._renderImages(rating);
        const date = new Date(rating.create_date).toLocaleDateString();
        
        return `
            <div class="rating-item mb-4 border-bottom pb-3">
                <div class="rating-header d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <div class="rating-stars mb-1">${stars}</div>
                        <strong>${rating.author_name}</strong>
                        <small class="text-muted ms-2">${date}</small>
                    </div>
                </div>
                ${rating.feedback ? `<div class="rating-content mb-2"><p>${rating.feedback}</p></div>` : ''}
                ${images}
            </div>
        `;
    },

    /**
     * Render star rating
     */
    _renderStars: function (rating) {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= rating) {
                stars += '<i class="fa fa-star text-warning"></i>';
            } else {
                stars += '<i class="fa fa-star-o text-muted"></i>';
            }
        }
        return stars;
    },

    /**
     * Render rating images
     */
    _renderImages: function (rating) {
        if (!rating.has_images) return '';
        
        let imagesHtml = '<div class="rating-images mt-2"><div class="row">';
        
        for (let i = 1; i <= 3; i++) {
            const smallImage = rating[`image_${i}_small`];
            const fullImage = rating[`image_${i}`];
            
            if (smallImage) {
                imagesHtml += `
                    <div class="col-auto">
                        <img src="data:image/png;base64,${smallImage}" 
                             class="rating-image-thumb img-thumbnail" 
                             alt="Review image ${i}"
                             data-full-image="data:image/png;base64,${fullImage}"
                             data-bs-toggle="modal" 
                             data-bs-target="#imageModal"
                             style="width: 80px; height: 80px; object-fit: cover; cursor: pointer;"/>
                    </div>
                `;
            }
        }
        
        imagesHtml += '</div></div>';
        return imagesHtml;
    },

    /**
     * Handle load more button click
     */
    _onLoadMore: function (ev) {
        ev.preventDefault();
        const productId = this.$('input[name="product_id"]').val();
        if (productId && this.hasMore) {
            this._loadRatings(productId, this.currentPage + 1);
        }
    },

    /**
     * Handle feedback input for character counting
     */
    _onFeedbackInput: function (ev) {
        const count = $(ev.currentTarget).val().length;
        this.$('#charCount').text(count);
        
        const charCount = this.$('#charCount');
        if (count > 900) {
            charCount.addClass('text-warning').removeClass('text-danger');
        } else if (count > 950) {
            charCount.addClass('text-danger').removeClass('text-warning');
        } else {
            charCount.removeClass('text-warning text-danger');
        }
    },

    /**
     * Show message with Bootstrap alert
     */
    _showMessage: function (message, type) {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Remove existing alerts
        this.$('.alert').remove();
        
        // Add new alert
        this.$el.prepend(alertHtml);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            this.$('.alert').fadeOut();
        }, 5000);
    }
});

// Initialize when DOM is ready
$(document).ready(function () {
    // Auto-initialize the widget
    if ($('.anonymous-rating-form').length) {
        new publicWidget.registry.AnonymousRatingWithImages().attachTo($('.anonymous-rating-form'));
    }
    
    // Event delegation for dynamically loaded images
    $(document).on('click', '.rating-image-thumb', function (ev) {
        const img = $(ev.currentTarget);
        const fullImageSrc = img.data('full-image') || img.attr('src');
        const alt = img.attr('alt');
        
        // Update modal content
        $('#modalImage').attr('src', fullImageSrc).attr('alt', alt);
        $('#imageModalLabel').text(alt);
    });
});