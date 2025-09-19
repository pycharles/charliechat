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

# Initialize router
router = APIRouter()

# Templates setup
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialize services
settings = get_settings()
chat_service = ChatService(settings)


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
            print(f"Found journal directory at: {journal_dir}")
            break
    
    entries = []
    
    if not journal_dir:
        print("Warning: No journal directory found in any expected location")
        print(f"Searched paths: {[str(p) for p in possible_paths]}")
        return entries
    
    # Filter out .beta.md files and load only .md files
    md_files = sorted(journal_dir.glob("*.md"), reverse=True)
    print(f"Found {len(md_files)} markdown files in journal directory")
    
    for md_file in md_files:
        # Skip .beta.md files
        if md_file.name.endswith('.beta.md'):
            print(f"Skipping beta file: {md_file.name}")
            continue
        
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
            
            # Convert markdown to HTML
            html_content = markdown.markdown(content)
            
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
            print(f"Error loading {md_file}: {e}")
            continue
    
    return entries


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Serve the main chat interface"""
    return templates.TemplateResponse("chat.html", {"request": request})


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
def blog(request: Request) -> HTMLResponse:
    """Serve the dev journal page"""
    journal_entries = load_journal_entries()
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "journal_entries": journal_entries
    })


@router.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post(request: Request, slug: str) -> HTMLResponse:
    """Serve blog page with specific article highlighted"""
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
        "request": request,
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


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy(request: Request) -> HTMLResponse:
    """Serve privacy policy page"""
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        "title": "Privacy Policy"
    })


@router.get("/terms", response_class=HTMLResponse)
def terms_of_service(request: Request) -> HTMLResponse:
    """Serve terms of service page"""
    return templates.TemplateResponse("terms.html", {
        "request": request,
        "title": "Terms of Service"
    })


@router.post("/chat")
async def chat(
    request: Request,
    session_id: str | None = Form(None),
    text: str | None = Form(None),
    session_state: str | None = Form(None),
    voice_style: str | None = Form("normal")
):
    """
    Handle chat requests (both HTMX and JSON)
    
    - If HX-Request header is present (HTMX), returns HTML fragment
    - Otherwise, returns JSON response
    """
    # Use request ID from middleware or generate one
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    debug_logger.log_route(
        request_id,
        f"Received chat request - Session: {session_id}, Text: '{text[:50] if text else 'None'}{'...' if text and len(text) > 50 else ''}', Voice: {voice_style}",
        request
    )
    
    if not session_id or not text:
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
            debug_logger.log_route(
                request_id,
                f"Received session state: {str(parsed_session_state)[:200]}{'...' if len(str(parsed_session_state)) > 200 else ''}",
                request
            )
        except json.JSONDecodeError as e:
            debug_logger.log_route(
                request_id,
                f"Failed to parse session state JSON: {e}. Raw: {session_state[:100]}...",
                request
            )
            parsed_session_state = None
    else:
        debug_logger.log_route(
            request_id,
            "No session state provided - starting new conversation",
            request
        )
    
    # Process chat through service layer
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
    debug_logger.log_route(
        request_id,
        f"Chat service completed for session {session_id}",
        request
    )
    
    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        debug_logger.log_route(
            request_id,
            "Processing HTMX response",
            request
        )
        
        # Debug: Log the actual response text being sent to frontend
        debug_logger.log_route(
            request_id,
            f"=== SENDING TO BROWSER ===",
            request
        )
        debug_logger.log_route(
            request_id,
            f"Browser response length: {len(response_text)} characters",
            request
        )
        debug_logger.log_route(
            request_id,
            f"Browser response content: {response_text}",
            request
        )
        
        # Verify response matches what was stored in last_answer
        if updated_session_state and "last_answer" in updated_session_state:
            last_answer = updated_session_state["last_answer"]
            if response_text == last_answer:
                debug_logger.log_route(
                    request_id,
                    f"✅ VERIFICATION: Browser response matches last_answer exactly",
                    request
                )
            else:
                debug_logger.log_route(
                    request_id,
                    f"❌ VERIFICATION FAILED: Browser response differs from last_answer",
                    request
                )
                debug_logger.log_route(
                    request_id,
                    f"last_answer length: {len(last_answer)}, Browser length: {len(response_text)}",
                    request
                )
        else:
            debug_logger.log_route(
                request_id,
                f"⚠️ No last_answer found in session state for verification",
                request
            )
            
        debug_logger.log_route(
            request_id,
            f"=== END BROWSER RESPONSE ===",
            request
        )
        
        # Process Markdown in bot responses for formatting
        import markdown
        html_content = markdown.markdown(response_text, extensions=['nl2br'])
        
        # Debug: Log the HTML content after markdown processing
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
