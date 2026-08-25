/**
 * Video Dialogue Locator - API Client & Polling Utility
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Submit a new dialogue location job
 */
export async function createJob(url, targetText, modelSize = 'base', threshold = 0.9) {
  const endpoint = `${API_BASE}/jobs`;
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      url: url.trim(),
      target_text: targetText.trim(),
      model_size: modelSize,
      threshold: parseFloat(threshold),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Server error (${response.status})`);
  }

  return response.json();
}

/**
 * Fetch status and results for a specific job
 */
export async function getJob(jobId) {
  const endpoint = `${API_BASE}/jobs/${encodeURIComponent(jobId)}`;
  const response = await fetch(endpoint, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Failed to fetch job (${response.status})`);
  }

  return response.json();
}

/**
 * Fetch list of all historical jobs
 */
export async function listJobs() {
  const endpoint = `${API_BASE}/jobs`;
  const response = await fetch(endpoint, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    return [];
  }

  return response.json();
}

/**
 * Poll job status until terminal state or timeout
 */
export function pollJobStatus(jobId, onUpdate, pollIntervalMs = 2000, timeoutMs = 600000) {
  let isCancelled = false;
  const startTime = Date.now();

  const poll = async () => {
    if (isCancelled) return;

    try {
      if (Date.now() - startTime > timeoutMs) {
        onUpdate({
          status: 'failed',
          error: 'Job timed out after 10 minutes. Please check the backend server logs.',
        });
        return;
      }

      const jobData = await getJob(jobId);
      if (isCancelled) return;

      onUpdate(jobData);

      const terminalStatuses = ['completed', 'failed'];
      if (!terminalStatuses.includes(jobData.status)) {
        setTimeout(poll, pollIntervalMs);
      }
    } catch (err) {
      if (isCancelled) return;
      onUpdate({
        status: 'failed',
        error: err.message || 'Error communicating with backend service',
      });
    }
  };

  poll();

  // Return cancellation callback
  return () => {
    isCancelled = true;
  };
}

/**
 * Resolve full image URL for extracted frames
 */
export function resolveImageUrl(imagePath) {
  if (!imagePath) return '';
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    return imagePath;
  }
  // In our backend, image_url is returned as /output/... or image_path is relative to output base
  if (imagePath.startsWith('/output/')) {
    return `${API_BASE}${imagePath}`;
  }
  if (imagePath.startsWith('output/')) {
    return `${API_BASE}/${imagePath}`;
  }
  return `${API_BASE}/output/${imagePath.replace(/^\\+|^\/+/, '')}`;
}
