// Bio modal functionality
function initBioModal() {
  const bioModal = document.getElementById('bio-modal');
  const bioOverlay = document.getElementById('bio-modal-overlay');
  const bioClose = document.getElementById('bio-modal-close');
  
  function openBioModal() {
    bioModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
  
  function closeBioModal() {
    bioModal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
  
  // Event listeners
  bioOverlay.addEventListener('click', closeBioModal);
  bioClose.addEventListener('click', closeBioModal);
  
  // Close modal with Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && bioModal.style.display === 'flex') {
      closeBioModal();
    }
  });
  
  // Make openBioModal globally available
  window.openBioModal = openBioModal;
}

// Contact functionality
function initContact() {
  function openContactModal() {
    // Build email dynamically to avoid scraping
    const email = 'charles.r.obrien' + '+' + 'charliechat' + '@gmail.com';
    
    // Copy email to clipboard
    navigator.clipboard.writeText(email).then(function() {
      // Show success notification
      showNotification('Email copied to clipboard! You can now paste it in your email client.', 'success');
    }).catch(function(err) {
      console.error('Could not copy text: ', err);
      // Fallback: show email in alert
      alert(`Email: ${email}\n\nPlease copy this email address to send a message.`);
    });
  }
  
  // Make openContactModal globally available
  window.openContactModal = openContactModal;
}

// Notification system
function showNotification(message, type = 'info') {
  // Remove existing notification
  const existing = document.querySelector('.notification');
  if (existing) existing.remove();
  
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <div class="notification-content">
      <span class="notification-message">${message}</span>
      <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;
  
  // Add to page
  document.body.appendChild(notification);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (notification.parentElement) {
      notification.remove();
    }
  }, 5000);
}

// Navbar functionality
function initNavbar() {
  const navLinks = document.querySelectorAll('.nav-link');
  
  navLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      const targetTab = this.getAttribute('data-tab');
      const href = this.getAttribute('href');
      
      // If it's a real URL (not just #), let the browser handle it
      if (href && href !== '#' && !href.startsWith('#')) {
        return; // Don't prevent default, let browser navigate
      }
      
      e.preventDefault();
      
      // Handle different tab types
      if (targetTab === 'bio') {
        openBioModal();
        return; // Don't change active states for modal actions
      } else if (targetTab === 'contact') {
        openContactModal();
        return; // Don't change active states for modal actions
      }
    });
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    initNavbar();
    initBioModal();
    initContact();
  });
} else {
  initNavbar();
  initBioModal();
  initContact();
}
