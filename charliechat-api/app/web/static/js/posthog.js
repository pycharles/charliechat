// PostHog client-side analytics
(function() {
  if (!window.POSTHOG_API_KEY) return;

  const startTime = Date.now();

  posthog.init(window.POSTHOG_API_KEY, {
    api_host: 'https://us.i.posthog.com',
    autocapture: true,
    capture_pageview: true,
    disable_session_recording: false
  });

  // Helper function to get cookie value
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  // Get session_id from cookie and register with PostHog
  const sessionId = getCookie("session_id");
  
  // Attach current URL, referrer, and session_id as properties
  posthog.register({
    "$current_url": window.location.href,
    "$referrer": document.referrer || "",
    "session_id": sessionId || null
  });

  // Capture $pageleave for session duration tracking
  window.addEventListener('beforeunload', function() {
    posthog.capture('$pageleave', { session_duration_ms: Date.now() - startTime });
  });
})();
