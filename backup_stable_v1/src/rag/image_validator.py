"""
Image URL Validator
Validates that URLs are actual images, not article pages.
"""
import re


def is_valid_image_url(url: str) -> bool:
    """
    Check if URL points to an actual image resource.
    
    Args:
        url: Image URL to validate
        
    Returns:
        True if URL is a valid image
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Reject article URLs explicitly (common false positive)
    if 'index.php' in url_lower and 'option=com_content' in url_lower:
        return False
        
    # Reject UI/Counter images based on keywords in URL
    invalid_keywords = ['counter', 'button', 'template', 'icon', 'print', 'email', 'pdf', 'stats', 'mod_vvisit']
    if any(kw in url_lower for kw in invalid_keywords):
        return False
    
    # Check for image file extensions (Strict check)
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.tiff']
    if any(url_lower.endswith(ext) for ext in image_extensions):
        return True
    
    # Check for /images/ path (Must be an image path, not just 'images' in query param)
    # And must NOT look like a php script unless it ends in an extension
    if '/images/' in url_lower:
        if '.php' in url_lower and not any(url_lower.endswith(ext) for ext in image_extensions):
            return False
        return True
    
    return False


def filter_valid_images(images: list) -> list:
    """
    Filter list of image dicts to only valid image URLs.
    
    Args:
        images: List of image dicts with 'url', 'alt', 'caption'
        
    Returns:
        Filtered list of valid images
    """
    if not images:
        return []
    
    valid_images = []
    for img in images:
        url = img.get('url', '')
        if is_valid_image_url(url):
            valid_images.append(img)
    
    return valid_images
