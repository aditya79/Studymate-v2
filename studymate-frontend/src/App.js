import React, { useState, useEffect } from 'react';
import './App.css';
import { Upload, Book, FileText, CheckCircle, ChevronLeft, ChevronRight, RotateCw, Trash2, Cloud } from 'lucide-react';

function App() {
  // state for authentication
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // state for files
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  
  // state for flashcards
  const [showFlashcards, setShowFlashcards] = useState(false);
  const [currentFlashcards, setCurrentFlashcards] = useState([]);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [currentDocName, setCurrentDocName] = useState('');
  
  // state for stats
  const [userStats, setUserStats] = useState({ total_files: 0, total_cards: 0 });

  // backend API URL
  const API_URL = 'http://localhost:5000/api';
  
  // Google Client ID 
  const GOOGLE_CLIENT_ID = '268330777379-evaefa7i8q2gl0tpeuakj2qdi6sdunj7.apps.googleusercontent.com';

  // check if google client id is configured
  const isGoogleConfigured = GOOGLE_CLIENT_ID && !GOOGLE_CLIENT_ID.includes('YOUR_GOOGLE');

  // load google sign-in library
  useEffect(() => {
    if (!isGoogleConfigured) {
      console.warn('Google Client ID not configured!');
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);
    
    script.onload = () => {
      console.log('Google Sign-In library loaded');
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleLogin
        });
        renderGoogleButton();
      }
    };
    
    script.onerror = () => {
      console.error('Failed to load Google Sign-In library');
    };
    
    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  // check if user is already logged in
  useEffect(() => {
    checkAuth();
  }, []);

  // check authentication status
  async function checkAuth() {
    try {
      const response = await fetch(`${API_URL}/check-auth`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.authenticated) {
        setUser(data.user);
        loadUserFiles();
      }
      setLoading(false);
    } catch (error) {
      console.error('Auth check error:', error);
      setLoading(false);
    }
  }

  // handle google login callback
  async function handleGoogleLogin(response) {
    try {
      console.log('Google login initiated');
      
      const result = await fetch(`${API_URL}/google-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          credential: response.credential
        })
      });
      
      const data = await result.json();
      
      if (data.status === 'success') {
        console.log('Login successful:', data.user.email);
        setUser(data.user);
        loadUserFiles();
        
        // render the button again for logout functionality
        renderGoogleButton();
      } else {
        alert('Login failed: ' + data.message);
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Could not connect to server');
    }
  }

  // render google sign-in button
  function renderGoogleButton() {
    if (window.google && !user) {
      setTimeout(() => {
        const buttonDiv = document.getElementById('google-signin-button');
        if (buttonDiv) {
          window.google.accounts.id.renderButton(
            buttonDiv,
            { 
              theme: 'outline', 
              size: 'large',
              text: 'signin_with',
              width: 320
            }
          );
        }
      }, 100);
    }
  }

  // call renderGoogleButton when component mounts
  useEffect(() => {
    renderGoogleButton();
  }, [user]);

  // handle logout
  async function handleLogout() {
    try {
      await fetch(`${API_URL}/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      
      setUser(null);
      setUploadedDocs([]);
      setUserStats({ total_files: 0, total_cards: 0 });
      console.log('Logged out');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  // load user's files from backend
  async function loadUserFiles() {
    try {
      const response = await fetch(`${API_URL}/files`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.files) {
        setUploadedDocs(data.files);
        console.log(`Loaded ${data.files.length} files`);
      }
      
      // load stats
      loadStats();
    } catch (error) {
      console.error('Error loading files:', error);
    }
  }

  // load user statistics
  async function loadStats() {
    try {
      const response = await fetch(`${API_URL}/stats`, {
        credentials: 'include'
      });
      const data = await response.json();
      setUserStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  }

  // handle file selection
  function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
      const fileName = file.name.toLowerCase();
      
      if (fileName.endsWith('.txt') || fileName.endsWith('.pdf') || 
          fileName.endsWith('.doc') || fileName.endsWith('.docx')) {
        setSelectedFile(file);
        setUploadStatus('');
      } else {
        alert('Please select PDF, TXT, DOC, or DOCX file');
        e.target.value = '';
      }
    }
  }

  // upload file to backend
  async function handleUpload() {
    if (!selectedFile) {
      alert('Please select a file');
      return;
    }

    setIsUploading(true);
    setUploadStatus('uploading');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      const data = await response.json();

      if (data.status === 'success') {
        setUploadStatus('success');
        setSelectedFile(null);
        document.getElementById('fileInput').value = '';
        
        // reload files
        loadUserFiles();
        
        console.log(`Uploaded with ${data.flashcard_count} flashcards`);
      } else {
        alert('Upload failed: ' + data.message);
        setUploadStatus('');
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Could not upload file');
      setUploadStatus('');
    }

    setIsUploading(false);
  }

  // view flashcards
  async function viewFlashcards(fileId, filename) {
    try {
      console.log('Loading flashcards for:', filename);
      
      const response = await fetch(`${API_URL}/flashcards/${fileId}`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.status === 'success' && data.flashcards.length > 0) {
        setCurrentFlashcards(data.flashcards);
        setCurrentDocName(filename);
        setShowFlashcards(true);
        setCurrentCardIndex(0);
        setIsFlipped(false);
      } else {
        alert('No flashcards found');
      }
    } catch (error) {
      console.error('Error loading flashcards:', error);
      alert('Could not load flashcards');
    }
  }

  // delete file
  async function deleteDocument(fileId, filename) {
    if (!window.confirm(`Delete "${filename}"?`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/files/${fileId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        loadUserFiles();
        alert('Document deleted');
      } else {
        alert('Delete failed');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Could not delete');
    }
  }

  // flashcard navigation
  function nextCard() {
    if (currentCardIndex < currentFlashcards.length - 1) {
      setCurrentCardIndex(currentCardIndex + 1);
      setIsFlipped(false);
    }
  }

  function prevCard() {
    if (currentCardIndex > 0) {
      setCurrentCardIndex(currentCardIndex - 1);
      setIsFlipped(false);
    }
  }

  function flipCard() {
    setIsFlipped(!isFlipped);
  }

  function closeFlashcards() {
    setShowFlashcards(false);
    setCurrentFlashcards([]);
    setCurrentCardIndex(0);
    setIsFlipped(false);
  }

  // loading screen
  if (loading) {
    return (
      <div className="loading-container">
        <div className="logo-circle">
          <Book size={48} color="white" />
        </div>
        <p>Loading StudyMate...</p>
      </div>
    );
  }

  // login screen
  if (!user) {
    return (
      <div className="login-container">
        <div className="login-box">
          <div className="login-header">
            <div className="logo-circle">
              <Book size={32} color="white" />
            </div>
            <h1>StudyMate</h1>
            <p>AI-Powered Flashcard Generator</p>
            <p className="tech-stack">MongoDB + Flask + React</p>
          </div>

          <div id="google-signin-button" className="google-button-container"></div>

          <div className="features">
            <p> Auto-generate flashcards from notes</p>
            <p>Store in MongoDB cloud database</p>
            <p> Secure Google authentication</p>
          </div>
        </div>
      </div>
    );
  }

  // flashcard viewer
  if (showFlashcards) {
    const currentCard = currentFlashcards[currentCardIndex];
    
    return (
      <div className="flashcard-viewer">
        <div className="flashcard-header">
          <button onClick={closeFlashcards} className="back-button">
            <ChevronLeft size={20} />
            Back to Documents
          </button>
          <div className="flashcard-title">
            <h2>{currentDocName}</h2>
            <p>Card {currentCardIndex + 1} of {currentFlashcards.length}</p>
          </div>
        </div>

        <div className="flashcard-content">
          <div className={`flashcard ${isFlipped ? 'flipped' : ''}`} onClick={flipCard}>
            <div className="flashcard-inner">
              <div className="flashcard-front">
                <div className="card-label">Question</div>
                <div className="card-text">{currentCard.question}</div>
                <div className="flip-hint">Click to flip</div>
              </div>
              <div className="flashcard-back">
                <div className="card-label">Answer</div>
                <div className="card-text">{currentCard.answer}</div>
                <div className="flip-hint">Click to flip back</div>
              </div>
            </div>
          </div>

          <div className="flashcard-controls">
            <button 
              onClick={prevCard} 
              disabled={currentCardIndex === 0}
              className="control-button"
            >
              <ChevronLeft size={24} />
              Previous
            </button>
            
            <button onClick={flipCard} className="control-button flip-btn">
              <RotateCw size={24} />
              Flip Card
            </button>
            
            <button 
              onClick={nextCard} 
              disabled={currentCardIndex === currentFlashcards.length - 1}
              className="control-button"
            >
              Next
              <ChevronRight size={24} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // main app
  return (
    <div className="app-container">
      <div className="header">
        <div className="header-content">
          <div className="header-left">
            <div className="header-logo">
              <Book size={24} color="white" />
            </div>
            <div>
              <h1>StudyMate</h1>
              <p>Welcome, {user.name || user.email}</p>
            </div>
          </div>
          <div className="header-right">
            {user.picture && (
              <img src={user.picture} alt="Profile" className="user-avatar" />
            )}
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="main-content">
        <div className="stats-card">
          <div className="stat-item">
            <Cloud size={32} color="#4F46E5" />
            <div>
              <p className="stat-number">{userStats.total_files}</p>
              <p className="stat-label">Documents in MongoDB</p>
            </div>
          </div>
          <div className="stat-item">
            <Book size={32} color="#10B981" />
            <div>
              <p className="stat-number">{userStats.total_cards}</p>
              <p className="stat-label">Flashcards Generated</p>
            </div>
          </div>
        </div>

        <div className="upload-card">
          <h2>Upload Your Notes</h2>
          <p className="subtitle">Upload TXT files for best results (PDF/DOC supported)</p>

          <div className="upload-area">
            <Upload size={48} color="#999" />
            <p className="file-name">
              {selectedFile ? selectedFile.name : 'Choose a file'}
            </p>
            <p className="file-info">Supported: TXT, PDF, DOC, DOCX (Max 16MB)</p>
            
            <input
              id="fileInput"
              type="file"
              onChange={handleFileSelect}
              accept=".pdf,.txt,.doc,.docx"
              style={{ display: 'none' }}
            />
            <label htmlFor="fileInput" className="browse-button">
              Browse Files
            </label>
          </div>

          {selectedFile && (
            <div className="upload-actions">
              <button 
                onClick={handleUpload} 
                disabled={isUploading}
                className="upload-button"
              >
                {isUploading ? 'Uploading to MongoDB...' : (
                  <>
                    <Upload size={20} />
                    Upload & Generate Flashcards
                  </>
                )}
              </button>
              <button onClick={() => {
                setSelectedFile(null);
                document.getElementById('fileInput').value = '';
              }} className="cancel-button">
                Cancel
              </button>
            </div>
          )}

          {uploadStatus === 'success' && (
            <div className="success-message">
              <CheckCircle size={20} />
              <p>Uploaded to MongoDB! Flashcards generated successfully.</p>
            </div>
          )}
        </div>

        {uploadedDocs.length > 0 ? (
          <div className="documents-card">
            <h3>Your Saved Documents (MongoDB Cloud)</h3>
            <div className="documents-list">
              {uploadedDocs.map((doc) => (
                <div key={doc.id} className="document-item">
                  <div className="document-info">
                    <FileText size={32} color="#4F46E5" />
                    <div>
                      <p className="doc-name">{doc.filename}</p>
                      <p className="doc-details">
                        {(doc.size / 1024).toFixed(2)} KB • {doc.flashcard_count} cards • {new Date(doc.upload_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="document-actions">
                    <button 
                      onClick={() => viewFlashcards(doc.id, doc.filename)} 
                      className="view-button"
                    >
                      View Flashcards
                    </button>
                    <button 
                      onClick={() => deleteDocument(doc.id, doc.filename)} 
                      className="delete-button"
                      title="Delete"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <Upload size={64} color="#D1D5DB" />
            <h3>No documents yet</h3>
            <p>Upload your first document to get started!</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;