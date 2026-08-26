import React, { useState, useEffect, useRef } from 'react';
import URLInput from './components/URLInput';
import TargetTextInput from './components/TargetTextInput';
import JobStatus from './components/JobStatus';
import ResultDisplay from './components/ResultDisplay';
import JobHistory from './components/JobHistory';
import { createJob, pollJobStatus, getJob } from './api';
import { Search, Sparkles, Film, AlertCircle } from 'lucide-react';

export default function App() {
  const [url, setUrl] = useState('');
  const [targetText, setTargetText] = useState('');
  const [modelSize, setModelSize] = useState('base');
  const [threshold, setThreshold] = useState(0.9);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);
  const [formError, setFormError] = useState(null);

  const cancelPollingRef = useRef(null);

  // Clean up active polling on unmount
  useEffect(() => {
    return () => {
      if (cancelPollingRef.current) {
        cancelPollingRef.current();
      }
    };
  }, []);

  const handleSelectSample = (sampleUrl, samplePhrase) => {
    setUrl(sampleUrl);
    setTargetText(samplePhrase);
    setFormError(null);
  };

  const handleSelectHistoricalJob = (historicalJob) => {
    if (cancelPollingRef.current) {
      cancelPollingRef.current();
    }
    setCurrentJob(historicalJob);
    if (historicalJob.request) {
      setUrl(historicalJob.request.url || '');
      setTargetText(historicalJob.request.target_text || '');
      if (historicalJob.request.model_size) setModelSize(historicalJob.request.model_size);
      if (historicalJob.request.threshold) setThreshold(historicalJob.request.threshold);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!url.trim()) {
      setFormError('Please enter a valid video URL or server path.');
      return;
    }
    if (!targetText.trim()) {
      setFormError('Please enter a target dialogue phrase to search for.');
      return;
    }

    if (cancelPollingRef.current) {
      cancelPollingRef.current();
    }

    setIsSubmitting(true);
    setCurrentJob(null);

    try {
      const response = await createJob(url, targetText, modelSize, threshold);
      const jobId = response.job_id;

      // Set initial queued status
      setCurrentJob({
        job_id: jobId,
        url,
        target_text: targetText,
        status: 'queued',
        created_at: new Date().toISOString(),
      });

      // Start live polling
      cancelPollingRef.current = pollJobStatus(
        jobId,
        (updatedJob) => {
          setCurrentJob(updatedJob);
          const terminalStates = ['completed', 'failed'];
          if (terminalStates.includes(updatedJob.status)) {
            setIsSubmitting(false);
          }
        },
        2000,
        600000 // 10 minute timeout
      );
    } catch (err) {
      setIsSubmitting(false);
      setFormError(err.message || 'Failed to submit search job. Please ensure the backend is running on port 8000.');
    }
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <div className="top-navbar">
        <div className="brand-badge">
          <span className="pulse-dot"></span>
          FastAPI & Whisper ASR Frame Locator
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          v1.0.0
        </div>
      </div>

      {/* Header */}
      <header className="app-header">
        <h1 className="main-title">
          Video Dialogue <span className="gradient-span">Locator</span>
        </h1>
        <p className="subtitle">
          Pinpoint exact video frames where spoken dialogue begins. Powered by OpenAI Whisper word-level timestamps, sliding-window fuzzy matching, and OpenCV frame extraction.
        </p>
      </header>

      {/* Main Content Area */}
      <main style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {/* Search Submission Card */}
        <div className="glass-card">
          <form onSubmit={handleSubmit} className="form-grid">
            <URLInput
              value={url}
              onChange={setUrl}
              disabled={isSubmitting}
              onSelectSample={handleSelectSample}
            />

            <TargetTextInput
              value={targetText}
              onChange={setTargetText}
              disabled={isSubmitting}
              modelSize={modelSize}
              onChangeModelSize={setModelSize}
              threshold={threshold}
              onChangeThreshold={setThreshold}
            />

            {formError && (
              <div className="alert-box alert-error">
                <AlertCircle size={20} style={{ flexShrink: 0 }} />
                <span>{formError}</span>
              </div>
            )}

            <button type="submit" className="btn-submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <span className="spinner"></span>
                  Processing Audio & Locating All Matching Frames...
                </>
              ) : (
                <>
                  <Search size={19} />
                  Locate Dialogue & Extract Frames
                </>
              )}
            </button>
          </form>

          {/* Search History Drawer */}
          <JobHistory
            onSelectJob={handleSelectHistoricalJob}
            currentJobId={currentJob?.job_id}
          />
        </div>

        {/* Live Job Progress Tracker */}
        {currentJob && <JobStatus job={currentJob} />}

        {/* Multi-Match Frame Visualizer on the Same Page */}
        {currentJob && currentJob.result && (
          <ResultDisplay
            result={currentJob.result}
            targetText={currentJob.request?.target_text || currentJob.target_text || targetText}
          />
        )}
      </main>

      {/* Footer */}
      <footer style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '3rem' }}>
        <p>Developed by Ankith Vijayyan</p>
      </footer>
    </div>
  );
}
