"""
Web routes for Charlie Chat

This module contains all FastAPI routes for the web interface.
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import uuid
import traceback
import re
from datetime import datetime
import markdown
from fastapi.responses import Response

from ..services import ChatService
from ..config import get_settings
from ..models.chat import ChatRequest, ChatResponse
from ..utils.debug_logger import debug_logger
from ..analytics.posthog_client import capture_event, flush_events
import functools
import inspect
import logging

# Initialize router
router = APIRouter()

# Templates setup
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialize services
settings = get_settings()
chat_service = ChatService(settings)


def get_common_context(request: Request) -> dict:
    """Get common template context including PostHog API key"""
    return {
        "request": request,
        "posthog_api_key": os.getenv("POSTHOG_API_KEY", "") if os.getenv("AWS_EXECUTION_ENV") else ""
    }


def track_event(event_name: str):
    """
    Decorator to capture a PostHog event when a route is hit.
    Works for sync and async routes, and automatically includes kwargs.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Track event for analytics
            if settings.debug:
                logging.getLogger(__name__).debug(f"track_event decorator called for {event_name}")
            
            # Call the route handler
            if inspect.iscoroutinefunction(func):
                response = await func(*args, **kwargs)
            else:
                response = func(*args, **kwargs)

            try:
                import logging
                from ..analytics.posthog_client import capture_event, flush_events
                
                # Try to find Request object in args first, then in kwargs
                request: Request | None = next((a for a in args if isinstance(a, Request)), None)
                if not request:
                    request = kwargs.get('request')
                
                if settings.debug:
                    logging.getLogger(__name__).debug(f"Request object found: {request is not None}")
                
                # Skip capture if no Request object found (e.g., in tests)
                if not request:
                    if settings.debug:
                        logging.getLogger(__name__).debug(f"No Request object found for {event_name}")
                    return response
                
                # Skip capture if PostHog is disabled (no API key)
                api_key = os.getenv("POSTHOG_API_KEY")
                if not api_key:
                    logging.getLogger(__name__).warning(f"PostHog disabled: No API key for event {event_name}")
                    return response
                
                props = {}

                if request:
                    # Sanitize user agent to prevent very long strings
                    user_agent = request.headers.get("user-agent", "")
                    if len(user_agent) > 300:
                        user_agent = user_agent[:300] + "..."
                    
                    props.update({
                        "path": str(request.url.path),
                        "method": request.method,
                        "$current_url": str(request.url),
                        "$referrer": request.headers.get("referer", ""),
                        "user_agent": user_agent
                    })
                    # Optional anonymized IP
                    client_ip = request.client.host if request.client else None
                    if client_ip:
                        ip_parts = client_ip.split(".")
                        if len(ip_parts) == 4:
                            ip_parts[-1] = "0"
                            props["ip_anonymized"] = ".".join(ip_parts)
                        else:
                            props["ip_anonymized"] = client_ip  # leave unchanged if IPv6

                props.update(kwargs)  # add route kwargs automatically

                # Add session_id from middleware to all events
                if hasattr(request.state, 'session_id'):
                    props["session_id"] = request.state.session_id
                    logging.getLogger(__name__).info(f"Found session_id: {request.state.session_id} for event {event_name}")
                else:
                    logging.getLogger(__name__).warning(f"No session_id found for event {event_name}")

                if event_name == "chat_message":
                    text = kwargs.get("text", "")
                    props.update({
                        "text": text[:200] if text else None,  # capture first 200 chars
                        "text_length": len(text) if text else 0,
                        "voice_style": kwargs.get("voice_style", "normal")
                    })
                elif event_name == "page_blog_post":
                    # Add blog post metadata with error handling
                    slug = kwargs.get("slug", "")
                    if slug:
                        try:
                            journal_entries = load_journal_entries()
                            target_entry = next((entry for entry in journal_entries if entry['slug'] == slug), None)
                            if target_entry:
                                props.update({
                                    "slug": slug,
                                    "title": target_entry.get("title", ""),
                                    "blog_post": True
                                })
                        except Exception as e:
                            # Log warning but don't crash the route
                            import logging
                            logging.getLogger(__name__).warning(f"Failed to load journal entries for blog post {slug}: {e}")
                            # If we can't load entries, just add the slug
                            props.update({
                                "slug": slug,
                                "blog_post": True
                            })

                # Use session_id as distinct_id for user tracking
                distinct_id = request.state.session_id if hasattr(request.state, 'session_id') else None
                logging.getLogger(__name__).info(f"Capturing {event_name} event for session {distinct_id}")
                
                try:
                    capture_event(event_name=event_name, properties=props, distinct_id=distinct_id)
                    flush_events()
                except Exception as capture_error:
                    logging.getLogger(__name__).error(f"PostHog capture failed for {event_name}: {capture_error}")
            except Exception as e:
                logging.getLogger(__name__).warning(f"PostHog capture failed for {event_name}: {e}")

            return response
        return wrapper
    return decorator


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title"""
    # Convert to lowercase
    slug = title.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def generate_sitemap() -> str:
    """Generate XML sitemap for all pages"""
    base_url = "https://charliechat.com"  # Update this to your actual domain
    journal_entries = load_journal_entries()
    
    # Get current timestamp for sitemap generation
    current_time = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Start building XML
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    # Add static pages
    static_pages = [
        {
            'url': f'{base_url}/',
            'lastmod': current_time,
            'changefreq': 'weekly',
            'priority': '1.0'
        },
        {
            'url': f'{base_url}/blog',
            'lastmod': current_time,
            'changefreq': 'weekly',
            'priority': '0.8'
        },
        {
            'url': f'{base_url}/privacy',
            'lastmod': current_time,
            'changefreq': 'monthly',
            'priority': '0.5'
        },
        {
            'url': f'{base_url}/terms',
            'lastmod': current_time,
            'changefreq': 'monthly',
            'priority': '0.5'
        },
        {
            'url': f'{base_url}/LICENSE',
            'lastmod': current_time,
            'changefreq': 'yearly',
            'priority': '0.3'
        }
    ]
    
    # Add static pages to sitemap
    for page in static_pages:
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{page["url"]}</loc>')
        xml_parts.append(f'    <lastmod>{page["lastmod"]}</lastmod>')
        xml_parts.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml_parts.append(f'    <priority>{page["priority"]}</priority>')
        xml_parts.append('  </url>')
    
    # Add blog posts with their actual modification dates
    for entry in journal_entries:
        # Get file modification date
        try:
            # Try to find the actual markdown file to get its modification date
            possible_paths = [
                Path(__file__).parent.parent.parent / "journal-md" / entry['filename'],
                Path(__file__).parent.parent / "journal-md" / entry['filename'],
                Path("/tmp/journal-md") / entry['filename'],
                Path("journal-md") / entry['filename']
            ]
            
            file_path = None
            for path in possible_paths:
                if path.exists():
                    file_path = path
                    break
            
            if file_path:
                # Get file modification time
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                lastmod = mod_time.strftime('%Y-%m-%d')
            else:
                # Fallback to current date if file not found
                lastmod = current_time
        except Exception:
            # Fallback to current date on any error
            lastmod = current_time
        
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{base_url}/blog/{entry["slug"]}</loc>')
        xml_parts.append(f'    <lastmod>{lastmod}</lastmod>')
        xml_parts.append('    <changefreq>monthly</changefreq>')
        xml_parts.append('    <priority>0.6</priority>')
        xml_parts.append('  </url>')
    
    # Close XML
    xml_parts.append('</urlset>')
    
    return '\n'.join(xml_parts)


def load_journal_entries() -> list:
    """Load and parse journal entries from markdown files"""
    # Try multiple possible locations for journal files
    possible_paths = [
        # Local development path
        Path(__file__).parent.parent.parent / "journal-md",
        # Lambda deployment path (journal files copied to app directory)
        Path(__file__).parent.parent / "journal-md",
        # Alternative Lambda path
        Path("/tmp/journal-md"),
        # Current working directory fallback
        Path("journal-md")
    ]
    
    journal_dir = None
    for path in possible_paths:
        if path.exists():
            journal_dir = path
            if settings.debug:
                print(f"Found journal directory at: {journal_dir}")
            break
    
    entries = []
    
    if not journal_dir:
        if settings.debug:
            print("Warning: No journal directory found in any expected location")
            print(f"Searched paths: {[str(p) for p in possible_paths]}")
        return entries
    
    # Filter out .beta.md files and load only .md files
    md_files = sorted(journal_dir.glob("*.md"), reverse=True)
    if settings.debug:
        print(f"Found {len(md_files)} markdown files in journal directory")
    
    for md_file in md_files:
        # Skip .beta.md files
        if md_file.name.endswith('.beta.md'):
            if settings.debug:
                print(f"Skipping beta file: {md_file.name}")
            continue
        
        if settings.debug:
            print(f"Processing journal file: {md_file.name}")
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title and date from filename
            # Handle date format: 2024-01-15-title -> Title (for blog) and 2024 (for nav)
            nav_title = None
            blog_title = None
            date_str = None
            nav_date = None
            
            if len(md_file.stem) >= 10 and md_file.stem[:4].isdigit():
                # Split date and title parts
                parts = md_file.stem.split('-', 3)  # Split into max 4 parts
                if len(parts) >= 4:
                    date_part = f"{parts[0]}-{parts[1]}-{parts[2]}"
                    title_part = parts[3].replace('-', ' ').title()
                    blog_title = title_part  # Just the title for blog
                    nav_title = title_part  # Just the title for nav
                    nav_date = date_part  # Full YYYY-MM-DD for nav
                    
                    # Full date for blog display
                    try:
                        date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                        date_str = date_obj.strftime('%B %d, %Y')
                    except ValueError:
                        pass
                else:
                    blog_title = md_file.stem.replace('-', ' ').title()
                    nav_title = md_file.stem.replace('-', ' ').title()
            else:
                blog_title = md_file.stem.replace('-', ' ').title()
                nav_title = md_file.stem.replace('-', ' ').title()
            
            # Convert markdown to HTML with error handling
            try:
                html_content = markdown.markdown(content)
            except Exception as e:
                if settings.debug:
                    print(f"Warning: Markdown conversion failed for {md_file.name}: {e}")
                # Fallback to plain text if markdown fails
                html_content = f"<pre>{content}</pre>"
            
            # Generate slug for URL
            slug = generate_slug(blog_title)
            
            # Generate meta description (first ~160 characters of content, stripped of markdown)
            meta_description = re.sub(r'[#*`]', '', content).strip()
            meta_description = re.sub(r'\s+', ' ', meta_description)
            meta_description = meta_description[:160] + '...' if len(meta_description) > 160 else meta_description
            
            entries.append({
                'title': blog_title,  # For blog display (no date)
                'nav_title': nav_title,  # For navigation display
                'date': date_str,  # Full date for blog display
                'nav_date': nav_date,  # Year only for navigation
                'content': html_content,
                'filename': md_file.name,
                'slug': slug,  # URL-friendly slug
                'meta_description': meta_description  # SEO meta description
            })
        except Exception as e:
            if settings.debug:
                print(f"Error loading {md_file}: {e}")
            continue
    
    return entries


# Home page route

@router.get("/", response_class=HTMLResponse)
@track_event("page_home")
def index(request: Request) -> HTMLResponse:
    """Serve the main chat interface"""
    """Serve the main chat interface"""
    try:
        if settings.debug:
            logging.getLogger(__name__).debug("Home page route called")
        context = get_common_context(request)
        return templates.TemplateResponse("chat.html", context)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in home page route: {e}")
        raise


# Add a test route for the exact same path to see if there's a conflict
@router.get("/test-home")
def test_home(request: Request) -> HTMLResponse:
    """Test route to verify home page logic works"""
    print("TEST_HOME_DEBUG: Test home route called")
    context = get_common_context(request)
    return templates.TemplateResponse("chat.html", context)


@router.get("/favicon.ico")
def favicon():
    """Redirect favicon requests to the SVG icon"""
    return RedirectResponse(url="/static/favicon.svg")


@router.get("/LICENSE", response_class=HTMLResponse)
def license(request: Request) -> HTMLResponse:
    """Serve the MIT License as HTML"""
    # Try multiple possible locations for LICENSE file
    possible_paths = [
        # Parent directory (development)
        Path(__file__).parent.parent.parent / "LICENSE",
        # Lambda deployment path (LICENSE copied to app directory)
        Path(__file__).parent.parent / "LICENSE",
        # Current working directory fallback
        Path("LICENSE"),
        # Parent of current working directory
        Path("..") / "LICENSE"
    ]
    
    license_path = None
    for path in possible_paths:
        if path.exists():
            license_path = path
            break
    
    if not license_path:
        raise HTTPException(status_code=404, detail="License file not found")
    
    try:
        with open(license_path, 'r', encoding='utf-8') as f:
            license_content = f.read()
        
        return templates.TemplateResponse("license.html", {
            "request": request,
            "license_content": license_content
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading license file: {str(e)}")


@router.get("/blog", response_class=HTMLResponse)
@track_event("page_blog")
def blog(request: Request) -> HTMLResponse:
    """Serve the dev journal page"""
    if settings.debug:
        logging.getLogger(__name__).debug("Blog page route called")
    journal_entries = load_journal_entries()
    return templates.TemplateResponse("blog.html", {
        **get_common_context(request),
        "journal_entries": journal_entries
    })


@router.get("/blog/{slug}", response_class=HTMLResponse)
@track_event("page_blog_post")
def blog_post(request: Request, slug: str) -> HTMLResponse:
    """Serve blog page with specific article highlighted"""
    if settings.debug:
        logging.getLogger(__name__).debug(f"Blog post route called for slug: {slug}")
    journal_entries = load_journal_entries()
    
    # Find the entry with matching slug
    target_entry = None
    for journal_entry in journal_entries:
        if journal_entry['slug'] == slug:
            target_entry = journal_entry
            break
    
    if not target_entry:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    return templates.TemplateResponse("blog.html", {
        **get_common_context(request),
        "journal_entries": journal_entries,
        "target_slug": slug  # Pass the target slug to highlight the correct article
    })


@router.get("/blog/{slug}/", response_class=HTMLResponse)
def blog_post_trailing_slash(request: Request, slug: str) -> HTMLResponse:
    """Redirect blog post with trailing slash to without trailing slash"""
    return RedirectResponse(url=f"/blog/{slug}", status_code=301)


@router.get("/sitemap")
def sitemap_html(request: Request):
    """Display HTML sitemap page"""
    journal_entries = load_journal_entries()
    
    # Convert journal entries to blog posts format for template
    blog_posts = []
    for entry in journal_entries:
        blog_posts.append({
            'title': entry['title'],
            'slug': entry['slug'],
            'date': entry['date']
        })
    
    return templates.TemplateResponse("sitemap.html", {
        "request": request,
        "title": "Sitemap",
        "blog_posts": blog_posts
    })


@router.get("/sitemap.xml")
def sitemap_xml():
    """Generate and return XML sitemap for search engines"""
    sitemap_xml = generate_sitemap()
    return Response(
        content=sitemap_xml,
        media_type="application/xml",
        headers={"Content-Type": "application/xml; charset=utf-8"}
    )


# Privacy policy route

@router.get("/privacy", response_class=HTMLResponse)
@track_event("page_privacy")
def privacy_policy(request: Request) -> HTMLResponse:
    """Serve privacy policy page"""
    """Serve privacy policy page"""
    try:
        if settings.debug:
            logging.getLogger(__name__).debug("Privacy page route called")
        context = get_common_context(request)
        return templates.TemplateResponse("privacy.html", {
            **context,
            "title": "Privacy Policy"
        })
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in privacy page route: {e}")
        raise


@router.get("/terms", response_class=HTMLResponse)
@track_event("page_terms")
def terms_of_service(request: Request) -> HTMLResponse:
    """Serve terms of service page"""
    return templates.TemplateResponse("terms.html", {
        **get_common_context(request),
        "title": "Terms of Service"
    })


@router.post("/chat")
@track_event("chat_message")
async def chat(
    request: Request,
    text: str | None = Form(None),
    session_state: str | None = Form(None),
    voice_style: str | None = Form("normal")
):
    """
    Handle chat requests (both HTMX and JSON)
    
    - If HX-Request header is present (HTMX), returns HTML fragment
    - Otherwise, returns JSON response
    """
    # Get session_id from middleware
    session_id = getattr(request.state, 'session_id', None)
    
    # Use request ID from middleware or generate one
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    if settings.debug:
        debug_logger.log_route(
            request_id,
            f"Received chat request - Session: {session_id}, Text: '{text[:50] if text else 'None'}{'...' if text and len(text) > 50 else ''}', Voice: {voice_style}",
            request
        )
    
    if not session_id or not text:
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"Missing required parameters - session_id: {session_id}, text: {text}",
                request
            )
        raise HTTPException(status_code=400, detail="session_id and text are required")
    
    # Parse session state if provided
    parsed_session_state = None
    if session_state:
        try:
            import json
            parsed_session_state = json.loads(session_state)
            if settings.debug:
                debug_logger.log_route(
                    request_id,
                    f"Received session state: {str(parsed_session_state)[:200]}{'...' if len(str(parsed_session_state)) > 200 else ''}",
                    request
                )
        except json.JSONDecodeError as e:
            if settings.debug:
                debug_logger.log_route(
                    request_id,
                    f"Failed to parse session state JSON: {e}. Raw: {session_state[:100]}...",
                    request
                )
            parsed_session_state = None
    else:
        if settings.debug:
            debug_logger.log_route(
                request_id,
                "No session state provided - starting new conversation",
                request
            )
    
    # Process chat through service layer
    if settings.debug:
        debug_logger.log_route(
            request_id,
            f"Calling chat_service.process_chat for session {session_id}",
            request
        )
    response_text, updated_session_state = await chat_service.process_chat(
        request_id=request_id,
        session_id=session_id,
        text=text,
        session_state=parsed_session_state,
        voice_style=voice_style,
        request=request
    )
    if settings.debug:
        debug_logger.log_route(
            request_id,
            f"Chat service completed for session {session_id}",
            request
        )
    
    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        if settings.debug:
            debug_logger.log_route(
                request_id,
                "Processing HTMX response",
                request
            )
        
        # Debug: Log the actual response text being sent to frontend
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"=== SENDING TO BROWSER ===",
                request
            )
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"Browser response length: {len(response_text)} characters",
                request
            )
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"Browser response content: {response_text}",
                request
            )
        
        # Verify response matches what was stored in last_answer
        if updated_session_state and "last_answer" in updated_session_state:
            last_answer = updated_session_state["last_answer"]
            if response_text == last_answer:
                if settings.debug:
                    debug_logger.log_route(
                        request_id,
                        f"✅ VERIFICATION: Browser response matches last_answer exactly",
                        request
                    )
            else:
                if settings.debug:
                    debug_logger.log_route(
                        request_id,
                        f"❌ VERIFICATION FAILED: Browser response differs from last_answer",
                        request
                    )
                if settings.debug:
                    debug_logger.log_route(
                        request_id,
                        f"last_answer length: {len(last_answer)}, Browser length: {len(response_text)}",
                        request
                    )
        else:
            if settings.debug:
                debug_logger.log_route(
                    request_id,
                    f"⚠️ No last_answer found in session state for verification",
                    request
                )
            
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"=== END BROWSER RESPONSE ===",
                request
            )
        
        # Process Markdown in bot responses for formatting with error handling
        import markdown
        try:
            html_content = markdown.markdown(response_text, extensions=['nl2br'])
        except Exception as e:
            if settings.debug:
                print(f"Warning: Markdown conversion failed for chat response: {e}")
            # Fallback to plain text if markdown fails
            html_content = response_text
        
        # Debug: Log the HTML content after markdown processing
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"HTML content after markdown: {html_content[:200]}{'...' if len(html_content) > 200 else ''}",
                request
            )
        
        # Return only bot message for HTMX (user message is added by JavaScript)
        # Include session state as a data attribute for JavaScript to read
        import json
        session_state_json = json.dumps(updated_session_state) if updated_session_state else "{}"
        
        # Log session state for debugging
        if settings.debug:
            debug_logger.log_route(
                request_id,
                f"Returning session state: {session_state_json[:200]}{'...' if len(session_state_json) > 200 else ''}",
                request
            )
        
        # Properly escape the JSON for HTML attribute
        import html
        escaped_session_state = html.escape(session_state_json, quote=True)
        
        return HTMLResponse(f"""
        <div class="message message-bot" data-session-state="{escaped_session_state}">
            <div class="bubble">{html_content}</div>
        </div>
        """)
    else:
        if settings.debug:
            debug_logger.log_route(
                request_id,
                "Processing JSON response",
                request
            )
        # Return JSON response for API
        return ChatResponse(
            messages=[{"contentType": "PlainText", "content": response_text}],
            session_state=updated_session_state
        )


# Debug routes removed
