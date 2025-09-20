// Initialize page on load
document.addEventListener('DOMContentLoaded', function() {
  // Session ID is now handled by server-side middleware
  // Initialize session state as empty object
  document.getElementById('session_state').value = '{}';
  
  // Initialize question counter for voice discovery
  window.questionCount = 0;
  window.voiceDiscoveryShown = false;
});

// Handle HTMX responses to update session state
document.addEventListener('htmx:afterRequest', function(event) {
  // Only handle chat requests
  if (event.detail.target && event.detail.target.id !== 'chat') {
    return;
  }
  
  // Ensure we don't return true from event listeners (which causes the async response error)
  
  console.log('HTMX afterRequest event fired, status:', event.detail.xhr.status);
  if (event.detail.xhr.status === 200) {
    // Increment question counter and check for voice discovery
    window.questionCount++;
    console.log('Question count:', window.questionCount);
    
    // Show voice discovery label after 2 questions
    if (window.questionCount >= 2 && !window.voiceDiscoveryShown) {
      showVoiceDiscoveryLabel();
    }
    
    try {
      // Try to extract session state from the response HTML
      const responseText = event.detail.xhr.responseText;
      console.log('Response text length:', responseText.length);
      
      // Look for data-session-state attribute in the response
      const sessionStateMatch = responseText.match(/data-session-state=['"]([^'"]+)['"]/);
      if (sessionStateMatch) {
        let sessionStateData = sessionStateMatch[1];
        console.log('Found session state in response:', sessionStateData.substring(0, 100) + '...');
        
        // Decode HTML entities (e.g., &quot; back to ")
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = sessionStateData;
        sessionStateData = tempDiv.textContent || tempDiv.innerText || '';
        
        try {
          const parsedState = JSON.parse(sessionStateData);
          document.getElementById('session_state').value = sessionStateData;
          console.log('Updated session state:', parsedState);
        } catch (e) {
          console.error('Failed to parse session state:', e, sessionStateData.substring(0, 100) + '...');
        }
      } else {
        console.log('No session state found in response');
      }
    } catch (error) {
      console.error('Error processing HTMX response:', error);
    }
  }
});

// Handle HTMX errors
document.addEventListener('htmx:responseError', function(event) {
  // Only handle chat requests
  if (event.detail.target && event.detail.target.id !== 'chat') {
    return;
  }
  
  console.error('HTMX Error:', event.detail);
  const input = document.querySelector('.composer-input');
  const sendBtn = document.querySelector('.composer-send');
  if (input) input.disabled = false;
  if (sendBtn) sendBtn.disabled = false;
  window.isRequestInProgress = false; // Reset request flag on error
  
  // Show error message to user
  const chat = document.getElementById('chat');
  if (chat) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message message-bot error fade-in';
    errorDiv.innerHTML = '<div class="bubble">Sorry, there was an error with your request. Please try again.</div>';
    chat.appendChild(errorDiv);
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
  }
});

// Keep input focused after submit for smoother chatting
document.addEventListener('htmx:afterOnLoad', function () {
  const input = document.querySelector('.composer-input');
  if (input) input.focus();
  const chat = document.getElementById('chat');
  if (chat) {
    // Smooth scroll to bottom
    chat.scrollTo({
      top: chat.scrollHeight,
      behavior: 'smooth'
    });
  }
});

// Replace pending placeholder with bot response
document.addEventListener('htmx:beforeSwap', function (evt) {
  const target = evt.detail.target;
  if (!target || target.id !== 'chat') return;
  const pending = document.getElementById('bot-pending');
  if (!pending) return;
  const html = evt.detail.xhr.responseText || '';
  const wrap = document.createElement('div');
  wrap.innerHTML = html;
  const botMessage = wrap.firstElementChild;
  if (!botMessage) return;
  
  // Add fade-in animation to bot response
  botMessage.classList.add('fade-in');
  
  pending.replaceWith(botMessage);
  evt.detail.shouldSwap = false; // prevent default append to #chat
  
  // Smooth scroll to bottom after bot response
  setTimeout(() => {
    const chat = document.getElementById('chat');
    if (chat) {
      chat.scrollTo({
        top: chat.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, 100);
});

// Simplified error handling - let HTMX handle most errors naturally
document.addEventListener('htmx:sendError', function (evt) {
  const target = evt.detail.target;
  if (!target || target.id !== 'chat') return;
  
  console.error('HTMX Send Error:', evt.detail);
  window.isRequestInProgress = false; // Reset request flag
});

// Centralized error handling function
function handleSessionError(message) {
  // Remove any pending message
  const pending = document.getElementById('bot-pending');
  if (pending) pending.remove();
  
  // Add error message
  const chat = document.getElementById('chat');
  const errorMessage = document.createElement('div');
  errorMessage.className = 'message message-bot fade-in';
  errorMessage.innerHTML = `
    <div class="bubble session-error">
      <div class="error-icon">⚠️</div>
      <div class="error-content">
        <strong>${message}</strong><br>
        <button class="refresh-btn" onclick="window.location.reload()">Refresh Page</button>
      </div>
    </div>
  `;
  chat.appendChild(errorMessage);
  chat.scrollTop = chat.scrollHeight;
  
  // Disable the input
  const input = document.querySelector('.composer-input');
  const sendBtn = document.querySelector('.composer-send');
  if (input) {
    input.disabled = true;
    input.placeholder = 'Session expired - please refresh the page';
  }
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.textContent = 'Session Expired';
  }
}

// Voice style selector functionality
let currentVoiceStyle = 'normal';

function initVoiceStyleSelector() {
  console.log('Initializing voice style selector...');
  const voiceButtons = document.querySelectorAll('.voice-style-btn');
  const voiceStyleInput = document.getElementById('voice_style_input');
  const chatVoiceSelector = document.querySelector('.chat-voice-selector');
  
  console.log('Found voice buttons:', voiceButtons.length);
  console.log('Found voice style input:', voiceStyleInput);
  console.log('Found chat voice selector:', chatVoiceSelector);
  
  // Make chat voice selector always visible but more prominent on hover
  const chat = document.getElementById('chat');
  if (chat && chatVoiceSelector) {
    // Voice selector is now always visible with reduced opacity
    chatVoiceSelector.classList.add('visible');
  }
  
  voiceButtons.forEach((button, index) => {
    console.log(`Button ${index}:`, button, 'data-style:', button.getAttribute('data-style'));
    
    // Set initial active state for the first button
    if (button.classList.contains('active')) {
      // CSS will handle the styling, just ensure the class is there
      button.classList.add('active');
    }
    
    button.addEventListener('click', function(e) {
      e.preventDefault();
      console.log('Button clicked:', this.getAttribute('data-style'));
      
      // Remove active class from all buttons
      voiceButtons.forEach(btn => {
        btn.classList.remove('active');
        console.log('Removed active from:', btn.getAttribute('data-style'));
      });
      
      // Add active class to clicked button
      this.classList.add('active');
      console.log('Added active to:', this.getAttribute('data-style'));
      
      // Update current voice style
      currentVoiceStyle = this.getAttribute('data-style');
      
      // Update the hidden input value
      if (voiceStyleInput) {
        voiceStyleInput.value = currentVoiceStyle;
        console.log('Updated input value to:', voiceStyleInput.value);
      }
      
      console.log('Voice style changed to:', currentVoiceStyle);
    });
  });
}

// Feedback modal functionality
function initFeedbackModal() {
  const feedbackBtn = document.getElementById('chat-feedback-fab');
  const feedbackModal = document.getElementById('feedback-modal');
  const feedbackOverlay = document.getElementById('feedback-modal-overlay');
  const feedbackClose = document.getElementById('feedback-modal-close');
  const feedbackCancel = document.getElementById('feedback-cancel');
  const feedbackForm = document.getElementById('feedback-form');
  const feedbackText = document.getElementById('feedback-text');
  const feedbackSubmit = document.getElementById('feedback-submit');
  const charCount = document.getElementById('char-count');
  const feedbackSuccess = document.getElementById('feedback-success');
  const sentimentInputs = document.querySelectorAll('input[name="sentiment"]');

  // Open modal
  function openModal() {
    feedbackModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    feedbackText.focus();
  }

  // Close modal
  function closeModal() {
    feedbackModal.style.display = 'none';
    document.body.style.overflow = 'auto';
    resetForm();
  }

  // Reset form
  function resetForm() {
    feedbackForm.style.display = 'block';
    feedbackSuccess.style.display = 'none';
    feedbackForm.reset();
    feedbackSubmit.disabled = true;
    charCount.textContent = '0';
  }

  // Update character count
  function updateCharCount() {
    const count = feedbackText.value.length;
    charCount.textContent = count;
    
    // Update submit button state
    const hasText = count > 0;
    const hasExperience = document.querySelector('input[name="experience"]:checked');
    feedbackSubmit.disabled = !(hasText && hasExperience);
  }

  // Event listeners
  feedbackBtn.addEventListener('click', openModal);
  feedbackOverlay.addEventListener('click', closeModal);
  feedbackClose.addEventListener('click', closeModal);
  feedbackCancel.addEventListener('click', closeModal);
  feedbackText.addEventListener('input', updateCharCount);
  
  // Add event listeners for experience radio buttons
  const experienceInputs = document.querySelectorAll('input[name="experience"]');
  experienceInputs.forEach(input => {
    input.addEventListener('change', updateCharCount);
  });

  // Form submission
  feedbackForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(feedbackForm);
    const data = {
      feedback: formData.get('feedback').trim(),
      experience: formData.get('experience'),
      name: formData.get('name').trim()
    };

    if (!data.feedback || !data.experience) {
      alert('Please provide feedback text and select your experience rating.');
      return;
    }

    try {
      feedbackSubmit.disabled = true;
      feedbackSubmit.textContent = 'Submitting...';

      const response = await fetch('/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        // Show success message
        feedbackForm.style.display = 'none';
        feedbackSuccess.style.display = 'block';
        
        // Auto-close after 2 seconds
        setTimeout(() => {
          closeModal();
        }, 2000);
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to submit feedback'}`);
      }
    } catch (error) {
      alert('Network error. Please try again.');
    } finally {
      feedbackSubmit.disabled = false;
      feedbackSubmit.textContent = 'Submit';
    }
  });

  // Close modal with Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && feedbackModal.style.display === 'flex') {
      closeModal();
    }
  });
}

// Voice Discovery Label Functions
function showVoiceDiscoveryLabel() {
  const label = document.getElementById('voiceDiscoveryLabel');
  const voiceSelector = document.querySelector('.chat-voice-selector');
  
  if (label && voiceSelector && !window.voiceDiscoveryShown) {
    // Show the label
    label.classList.add('show');
    
    // Show the voice selector with its normal fade animation
    voiceSelector.style.opacity = '1';
    voiceSelector.style.transform = 'translateX(0)';
    
    // Show all voice buttons with their normal animation
    const voiceButtons = voiceSelector.querySelectorAll('.voice-style-btn');
    voiceButtons.forEach(btn => {
      btn.style.opacity = '1';
      btn.style.transform = 'translateX(0)';
    });
    
    // Mark as shown
    window.voiceDiscoveryShown = true;
    
    // Hide the label after 4 seconds (2 seconds longer)
    setTimeout(() => {
      label.classList.remove('show');
    }, 4000);
    
    console.log('Voice discovery label shown');
  }
}

// Quick toggles to try background experiments
function setBg(mode) {
  document.body.classList.remove('bg-full', 'bg-split');
  if (mode === 'full') document.body.classList.add('bg-full');
  if (mode === 'split') document.body.classList.add('bg-full', 'bg-split');
}

// Catch the specific error to prevent console spam
window.addEventListener('unhandledrejection', function(event) {
  if (event.reason && event.reason.message && 
      event.reason.message.includes('A listener indicated an asynchronous response by returning true')) {
    console.log('Caught async response error (likely from browser extension)');
    event.preventDefault(); // Prevent the error from showing in console
  }
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    initVoiceStyleSelector();
    initFeedbackModal();
  });
} else {
  initVoiceStyleSelector();
  initFeedbackModal();
}
