from django import template
from urllib.parse import urlparse, parse_qs

register = template.Library()

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def youtube_embed_url(url):
    """Convert YouTube URL to embed URL."""
    if not url:
        return ''
    
    if 'youtube.com' in url:
        # Handle youtube.com URLs
        parsed = urlparse(url)
        video_id = parse_qs(parsed.query).get('v', [''])[0]
        if video_id:
            return f'https://www.youtube.com/embed/{video_id}'
    elif 'youtu.be' in url:
        # Handle youtu.be URLs
        parsed = urlparse(url)
        video_id = parsed.path.lstrip('/')
        if video_id:
            return f'https://www.youtube.com/embed/{video_id}'
    
    return url  # Return original URL if not YouTube