# Image Functionality Guide - Anonymous Product Rating

## Overview

This guide covers the enhanced image functionality that allows anonymous customers to submit pictures along with their product ratings. The implementation maintains theme layout compatibility while providing a rich user experience.

## Features

### 🖼️ **Image Upload Capabilities**

- **Multiple Images**: Up to 3 images per review
- **Format Support**: JPG, JPEG, PNG, GIF, WebP
- **Size Limits**: Maximum 5MB per image
- **Automatic Thumbnails**: Generated for performance
- **Preview Functionality**: Real-time image previews
- **Validation**: Client and server-side validation

### 🎨 **User Interface**

- **Drag & Drop**: Intuitive image upload interface
- **Progress Indicators**: Visual feedback during upload
- **Image Gallery**: Thumbnail display in reviews
- **Modal Viewer**: Full-size image viewing
- **Responsive Design**: Mobile-friendly interface

### 🔒 **Security & Performance**

- **File Validation**: Type and size checking
- **Image Processing**: Automatic thumbnail generation
- **Storage Optimization**: Efficient image storage
- **XSS Protection**: Secure image handling

## Implementation Details

### Database Schema

The following fields were added to the `anonymous.rating` model:

```python
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
```

### API Endpoints

#### Submit Rating with Images
```
POST /shop/product/anonymous_rating/submit_with_images
Content-Type: multipart/form-data

Parameters:
- product_id: Product ID
- rating: Rating value (1-5)
- author_name: Reviewer name
- author_email: Email (optional)
- feedback: Review text
- image_1: Image file (optional)
- image_2: Image file (optional)
- image_3: Image file (optional)
- recaptcha_token: reCAPTCHA token
```

#### Get Ratings with Images
```
POST /shop/product/{product_id}/anonymous_ratings_with_images
Content-Type: application/json

Parameters:
- page: Page number (default: 1)
- limit: Items per page (default: 10)

Response:
{
  "success": true,
  "ratings": [
    {
      "id": 1,
      "rating": 5.0,
      "feedback": "Great product!",
      "author_name": "John Doe",
      "create_date": "2024-01-01 12:00:00",
      "has_images": true,
      "image_count": 2,
      "image_1_small": "base64_encoded_thumbnail",
      "image_1": "base64_encoded_full_image",
      "image_2_small": "base64_encoded_thumbnail",
      "image_2": "base64_encoded_full_image"
    }
  ],
  "total_count": 10,
  "page": 1,
  "limit": 10,
  "has_more": false
}
```

## Usage Examples

### Basic Integration

To add image-enabled rating functionality to a product page:

```xml
<template id="my_product_page" inherit_id="website_sale.product">
    <xpath expr="//div[@id='product_details']" position="after">
        <div class="container mt-4">
            <t t-call="anonymous_product_rating.product_rating_integration"/>
        </div>
    </xpath>
</template>
```

### Compact Widget

For product listings or cards:

```xml
<template id="my_product_card" inherit_id="website_sale.products_item">
    <xpath expr="//div[hasclass('product_price')]" position="after">
        <t t-call="anonymous_product_rating.compact_rating_widget"/>
    </xpath>
</template>
```

### Inline Form

For quick rating submission:

```xml
<div class="quick-rating-section">
    <h5>Quick Rating</h5>
    <t t-call="anonymous_product_rating.inline_rating_form"/>
</div>
```

## Customization

### CSS Classes

The following CSS classes are available for customization:

```scss
// Main form container
.anonymous-rating-form {
    // Form styling
}

// Image upload areas
.image-upload-container {
    .image-upload-box {
        // Upload box styling
        
        &.has-image {
            // Styling when image is uploaded
        }
        
        &:hover {
            // Hover effects
        }
    }
}

// Image previews
.image-preview {
    img {
        // Preview image styling
    }
    
    .remove-image {
        // Remove button styling
    }
}

// Rating display
.rating-item {
    .rating-images {
        .rating-image-thumb {
            // Thumbnail styling
            
            &:hover {
                // Hover effects
            }
        }
    }
}

// Rating stars
.rating-stars {
    .rating-star {
        // Star styling
        
        &:hover,
        &.active {
            // Active/hover states
        }
    }
}
```

### JavaScript Events

Custom events are triggered for integration:

```javascript
// Listen for rating submission
$(document).on('rating:submitted', function(event, data) {
    console.log('Rating submitted:', data);
});

// Listen for rating loaded
$(document).on('rating:loaded', function(event, ratings) {
    console.log('Ratings loaded:', ratings);
});

// Listen for image upload
$(document).on('image:uploaded', function(event, imageData) {
    console.log('Image uploaded:', imageData);
});
```

### Template Customization

Override templates for custom layouts:

```xml
<!-- Custom rating form -->
<template id="my_custom_rating_form" inherit_id="anonymous_product_rating.anonymous_rating_form_with_images">
    <xpath expr="//div[hasclass('image-upload-container')]" position="replace">
        <!-- Your custom image upload interface -->
    </xpath>
</template>

<!-- Custom rating display -->
<template id="my_custom_rating_display" inherit_id="anonymous_product_rating.rating_item_with_images">
    <xpath expr="//div[hasclass('rating-images')]" position="replace">
        <!-- Your custom image display -->
    </xpath>
</template>
```

## Configuration

### Image Settings

Configure image handling in system parameters:

```python
# Maximum file size (bytes)
anonymous_product_rating.max_image_size = 5242880  # 5MB

# Allowed image formats
anonymous_product_rating.allowed_formats = 'jpg,jpeg,png,gif,webp'

# Thumbnail size
anonymous_product_rating.thumbnail_size = 256

# Full image max size
anonymous_product_rating.max_image_width = 1920
anonymous_product_rating.max_image_height = 1920
```

### Admin Interface

Manage ratings with images in the backend:

1. **Navigate to**: Website > Anonymous Ratings
2. **View Images**: Click on any rating to see uploaded images
3. **Bulk Operations**: Select multiple ratings for bulk actions
4. **Filtering**: Filter by "With Images" or "Without Images"

## Performance Considerations

### Image Optimization

- **Thumbnails**: Automatically generated for list views
- **Lazy Loading**: Images loaded on demand
- **Compression**: Automatic image compression
- **Caching**: Browser caching for better performance

### Database Impact

- **Storage**: Images stored as binary data in database
- **Indexing**: Optimized indexes for image-related queries
- **Cleanup**: Automatic cleanup of orphaned images

### Frontend Performance

- **Progressive Loading**: Images loaded progressively
- **Responsive Images**: Different sizes for different screens
- **Minified Assets**: Compressed CSS and JavaScript

## Security

### File Validation

- **Type Checking**: MIME type validation
- **Size Limits**: Configurable size restrictions
- **Extension Filtering**: Allowed file extensions only
- **Content Scanning**: Basic content validation

### XSS Protection

- **Image Processing**: Safe image handling
- **Content Sanitization**: Clean image metadata
- **Secure Display**: Safe image rendering

### Rate Limiting

- **Upload Limits**: Prevent abuse
- **IP Restrictions**: Per-IP upload limits
- **Time Windows**: Configurable time restrictions

## Troubleshooting

### Common Issues

1. **Images Not Uploading**
   - Check file size limits
   - Verify file format support
   - Check server upload limits
   - Verify disk space

2. **Images Not Displaying**
   - Check database storage
   - Verify image processing
   - Check browser console for errors
   - Verify template inheritance

3. **Performance Issues**
   - Enable image compression
   - Check thumbnail generation
   - Monitor database size
   - Optimize image queries

### Debug Mode

Enable debug logging for image functionality:

```python
import logging
logging.getLogger('addons.anonymous_product_rating.controllers.main').setLevel(logging.DEBUG)
logging.getLogger('addons.anonymous_product_rating.models.anonymous_rating').setLevel(logging.DEBUG)
```

### Error Messages

Common error messages and solutions:

- **"File too large"**: Reduce image size or increase limits
- **"Invalid file format"**: Use supported image formats
- **"Upload failed"**: Check server configuration
- **"Image processing error"**: Verify image integrity

## Migration

### Upgrading from Previous Versions

When upgrading to the image-enabled version:

1. **Database Migration**: New fields are added automatically
2. **Template Updates**: Update custom templates if needed
3. **Asset Updates**: Clear browser cache for new assets
4. **Configuration**: Review image-related settings

### Data Migration

Existing ratings remain unchanged. New image fields are optional and don't affect existing functionality.

## Best Practices

### For Developers

1. **Always validate images** on both client and server side
2. **Use thumbnails** for list views to improve performance
3. **Implement lazy loading** for better user experience
4. **Handle errors gracefully** with user-friendly messages
5. **Test with various image formats** and sizes

### For Administrators

1. **Monitor storage usage** regularly
2. **Set appropriate file size limits** based on your server capacity
3. **Enable image compression** to save space
4. **Regular cleanup** of old or unused images
5. **Monitor upload patterns** for potential abuse

### For Users

1. **Use high-quality images** that show the product clearly
2. **Keep file sizes reasonable** for faster uploads
3. **Use descriptive filenames** for better organization
4. **Avoid uploading sensitive information** in images
5. **Follow community guidelines** for appropriate content

## Support

For issues related to image functionality:

1. Check the error logs for specific error messages
2. Verify image file format and size requirements
3. Test with different browsers and devices
4. Check server configuration for upload limits
5. Contact support with specific error details

## Future Enhancements

Planned improvements for image functionality:

- **Image Editing**: Basic editing tools (crop, rotate)
- **Bulk Upload**: Multiple image selection
- **Cloud Storage**: Integration with cloud storage services
- **Image Recognition**: Automatic image tagging
- **Advanced Compression**: Better compression algorithms