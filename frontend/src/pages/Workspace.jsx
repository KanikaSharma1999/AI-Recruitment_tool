import { useState, useEffect, useRef } from 'react';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import API from '../api/client';
import toast from 'react-hot-toast';
import {
  MdFolder, MdNoteAdd, MdDelete, MdEdit, MdSearch,
  MdPictureAsPdf, MdCloudUpload, MdClose, MdVisibility,
  MdOpenInNew, MdInsertDriveFile, MdCalendarToday, MdContentPaste
} from 'react-icons/md';

export default function Workspace() {
  const [activeTab, setActiveTab] = useState('notes'); // 'notes' | 'documents'
  
  // Notes State
  const [notes, setNotes] = useState([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [noteSearch, setNoteSearch] = useState('');
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [selectedNote, setSelectedNote] = useState(null); // null for new, note object for editing
  const [noteForm, setNoteForm] = useState({ title: '', content: '' });
  
  // Documents State
  const [files, setFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [fileSearch, setFileSearch] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [docTitle, setDocTitle] = useState('');
  const fileInputRef = useRef(null);
  
  // View PDF State
  const [viewPdfUrl, setViewPdfUrl] = useState(null);
  const [viewPdfTitle, setViewPdfTitle] = useState('');

  // Fetch Notes
  const fetchNotes = async () => {
    setNotesLoading(true);
    try {
      const res = await API.get('/workspace/notes');
      setNotes(res.data);
    } catch (err) {
      toast.error('Failed to load notes');
    } finally {
      setNotesLoading(false);
    }
  };

  // Fetch Files
  const fetchFiles = async () => {
    setFilesLoading(true);
    try {
      const res = await API.get('/workspace/files');
      setFiles(res.data);
    } catch (err) {
      toast.error('Failed to load documents');
    } finally {
      setFilesLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
    fetchFiles();
  }, []);

  // Note actions
  const openNewNoteModal = () => {
    setSelectedNote(null);
    setNoteForm({ title: '', content: '' });
    setShowNoteModal(true);
  };

  const openEditNoteModal = (note) => {
    setSelectedNote(note);
    setNoteForm({ title: note.title, content: note.content });
    setShowNoteModal(true);
  };

  const saveNote = async (e) => {
    e.preventDefault();
    if (!noteForm.title.trim() || !noteForm.content.trim()) {
      toast.error('Please enter both title and content');
      return;
    }

    try {
      if (selectedNote) {
        // Edit existing note
        await API.put(`/workspace/notes/${selectedNote.id}`, noteForm);
        toast.success('Note updated!');
      } else {
        // Create new note
        await API.post('/workspace/notes', noteForm);
        toast.success('Note created!');
      }
      setShowNoteModal(false);
      fetchNotes();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save note');
    }
  };

  const deleteNote = async (id) => {
    if (!window.confirm('Are you sure you want to delete this note?')) return;
    try {
      await API.delete(`/workspace/notes/${id}`);
      toast.success('Note deleted');
      fetchNotes();
    } catch (err) {
      toast.error('Failed to delete note');
    }
  };

  // File Upload Handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      uploadPdf(droppedFiles[0]);
    }
  };

  const handleFileChange = (e) => {
    const selectedFiles = e.target.files;
    if (selectedFiles.length > 0) {
      uploadPdf(selectedFiles[0]);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  const uploadPdf = async (file) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Only PDF documents are supported');
      return;
    }

    // Limit to 15MB
    if (file.size > 15 * 1024 * 1024) {
      toast.error('File exceeds the 15MB size limit');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (docTitle.trim()) {
      formData.append('title', docTitle.trim());
    } else {
      formData.append('title', file.name.replace(/\.[^/.]+$/, ""));
    }

    setUploading(true);
    const uploadToastId = toast.loading(`Uploading ${file.name}...`);
    try {
      await API.post('/workspace/files', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success('PDF uploaded successfully!', { id: uploadToastId });
      setDocTitle('');
      fetchFiles();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to upload PDF', { id: uploadToastId });
    } finally {
      setUploading(false);
    }
  };

  const deleteFile = async (id) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await API.delete(`/workspace/files/${id}`);
      toast.success('Document deleted');
      fetchFiles();
      if (viewPdfUrl && viewPdfUrl.includes(id)) {
        setViewPdfUrl(null);
      }
    } catch (err) {
      toast.error('Failed to delete document');
    }
  };

  // Format File Size
  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  // Filters
  const filteredNotes = notes.filter(note =>
    note.title.toLowerCase().includes(noteSearch.toLowerCase()) ||
    note.content.toLowerCase().includes(noteSearch.toLowerCase())
  );

  const filteredFiles = files.filter(file =>
    file.title.toLowerCase().includes(fileSearch.toLowerCase()) ||
    file.filename.toLowerCase().includes(fileSearch.toLowerCase())
  );

  // Border accents for note cards
  const borderAccents = [
    'var(--primary)',
    'var(--success)',
    'var(--warning)',
    'var(--info)',
    'var(--purple)',
    '#ec4899', // pink
    '#14b8a6', // teal
  ];

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Recruiter Workspace" />
        
        <div className="page-body animate-fade" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Header Section */}
          <div className="flex-between page-header" style={{ marginBottom: 10 }}>
            <div>
              <h1 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <MdFolder style={{ color: 'var(--primary)' }} /> HR Workspace
              </h1>
              <p>Your centralized workspace for note-taking and PDF documents storage</p>
            </div>
            
            {activeTab === 'notes' ? (
              <button className="btn btn-primary" onClick={openNewNoteModal}>
                <MdNoteAdd style={{ fontSize: 18 }} /> Create Note
              </button>
            ) : (
              <div style={{ display: 'flex', gap: 10 }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Custom PDF title (optional)..."
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  style={{ width: 220, height: 38 }}
                />
                <button className="btn btn-primary" onClick={triggerFileInput} disabled={uploading}>
                  <MdCloudUpload style={{ fontSize: 18 }} /> Upload PDF
                </button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf"
                  style={{ display: 'none' }}
                />
              </div>
            )}
          </div>

          {/* Premium Tab Buttons */}
          <div style={{
            display: 'flex',
            gap: 4,
            borderBottom: '1px solid var(--border)',
            paddingBottom: 0,
            marginBottom: 10
          }}>
            <button
              onClick={() => setActiveTab('notes')}
              style={{
                padding: '12px 24px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'notes' ? '3px solid var(--primary)' : '3px solid transparent',
                color: activeTab === 'notes' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'notes' ? 700 : 500,
                fontSize: 14,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                transition: 'all 0.2s'
              }}
            >
              <MdContentPaste style={{ fontSize: 18, color: activeTab === 'notes' ? 'var(--primary)' : 'inherit' }} />
              Important Notes ({notes.length})
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              style={{
                padding: '12px 24px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'documents' ? '3px solid var(--primary)' : '3px solid transparent',
                color: activeTab === 'documents' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'documents' ? 700 : 500,
                fontSize: 14,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                transition: 'all 0.2s'
              }}
            >
              <MdPictureAsPdf style={{ fontSize: 18, color: activeTab === 'documents' ? 'var(--danger)' : 'inherit' }} />
              Important PDFs ({files.length})
            </button>
          </div>

          {/* Tab Contents */}
          {activeTab === 'notes' ? (
            /* ==================== NOTES TAB ==================== */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Search note bar */}
              <div className="card" style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 10 }}>
                <MdSearch style={{ color: 'var(--text-muted)', fontSize: 20 }} />
                <input
                  type="text"
                  placeholder="Search notes by title or content..."
                  value={noteSearch}
                  onChange={(e) => setNoteSearch(e.target.value)}
                  style={{
                    border: 'none',
                    outline: 'none',
                    width: '100%',
                    fontSize: 13.5,
                    background: 'transparent',
                    color: 'var(--text-primary)'
                  }}
                />
                {noteSearch && (
                  <button 
                    onClick={() => setNoteSearch('')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                  >
                    <MdClose />
                  </button>
                )}
              </div>

              {notesLoading ? (
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <div className="spinner" style={{ width: 30, height: 30 }} />
                  <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>Loading notes...</p>
                </div>
              ) : filteredNotes.length === 0 ? (
                <div className="card empty-state" style={{ padding: '60px 20px' }}>
                  <MdContentPaste style={{ fontSize: 60, color: 'var(--text-muted)', opacity: 0.6 }} />
                  <h3 style={{ marginTop: 16 }}>No Notes Found</h3>
                  <p style={{ maxWidth: 400, margin: '8px auto 0', color: 'var(--text-secondary)' }}>
                    {noteSearch ? "No notes matches your search query." : "Save important guidelines, recruitment strategies, or interviewer notes here."}
                  </p>
                  {!noteSearch && (
                    <button className="btn btn-primary" onClick={openNewNoteModal} style={{ marginTop: 20 }}>
                      Create Your First Note
                    </button>
                  )}
                </div>
              ) : (
                /* Grid of Notes */
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: 20
                }}>
                  {filteredNotes.map((note, index) => {
                    const borderAccent = borderAccents[index % borderAccents.length];
                    return (
                      <div
                        key={note.id}
                        className="card"
                        style={{
                          borderTop: `4px solid ${borderAccent}`,
                          minHeight: 180,
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          padding: 20,
                          cursor: 'pointer'
                        }}
                        onClick={() => openEditNoteModal(note)}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                              {note.title}
                            </h3>
                            <div 
                              style={{ display: 'flex', gap: 4, flexShrink: 0 }}
                              onClick={(e) => e.stopPropagation()} // Prevent card click
                            >
                              <button
                                onClick={() => openEditNoteModal(note)}
                                style={{
                                  background: 'rgba(79, 70, 229, 0.08)',
                                  border: 'none',
                                  borderRadius: 4,
                                  width: 28,
                                  height: 28,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  cursor: 'pointer',
                                  color: 'var(--primary)'
                                }}
                                title="Edit Note"
                              >
                                <MdEdit size={16} />
                              </button>
                              <button
                                onClick={() => deleteNote(note.id)}
                                style={{
                                  background: 'rgba(239, 68, 68, 0.08)',
                                  border: 'none',
                                  borderRadius: 4,
                                  width: 28,
                                  height: 28,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  cursor: 'pointer',
                                  color: 'var(--danger)'
                                }}
                                title="Delete Note"
                              >
                                <MdDelete size={16} />
                              </button>
                            </div>
                          </div>
                          
                          <p style={{
                            fontSize: 12.5,
                            color: 'var(--text-secondary)',
                            marginTop: 10,
                            lineHeight: 1.6,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            display: '-webkit-box',
                            WebkitLineClamp: 4,
                            WebkitBoxOrient: 'vertical'
                          }}>
                            {note.content}
                          </p>
                        </div>

                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          fontSize: 10.5,
                          color: 'var(--text-muted)',
                          marginTop: 16,
                          borderTop: '1px solid var(--border)',
                          paddingTop: 10
                        }}>
                          <MdCalendarToday size={12} />
                          <span>
                            Updated {new Date(note.updated_at || note.created_at).toLocaleDateString()} at{' '}
                            {new Date(note.updated_at || note.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* ==================== DOCUMENTS TAB ==================== */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Drag and Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={triggerFileInput}
                className={`dropzone ${isDragging ? 'active' : ''}`}
                style={{
                  border: uploading ? '1.5px dashed var(--border)' : '1.5px dashed var(--primary)',
                  background: isDragging ? 'rgba(79, 70, 229, 0.04)' : 'var(--bg-secondary)',
                  padding: '40px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 12,
                  pointerEvents: uploading ? 'none' : 'auto'
                }}
              >
                {uploading ? (
                  <>
                    <div className="spinner" style={{ width: 32, height: 32 }} />
                    <h4 style={{ fontWeight: 600 }}>Uploading PDF Document...</h4>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Processing and storing files securely</p>
                  </>
                ) : (
                  <>
                    <MdCloudUpload style={{ fontSize: 44, color: 'var(--primary)' }} />
                    <div>
                      <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                        Drag & Drop your important PDF here
                      </h4>
                      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                        Or click to browse from local files. Maximum file size: 15MB.
                      </p>
                    </div>
                  </>
                )}
              </div>

              {/* Search file bar */}
              <div className="card" style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 10 }}>
                <MdSearch style={{ color: 'var(--text-muted)', fontSize: 20 }} />
                <input
                  type="text"
                  placeholder="Search uploaded PDFs by title or filename..."
                  value={fileSearch}
                  onChange={(e) => setFileSearch(e.target.value)}
                  style={{
                    border: 'none',
                    outline: 'none',
                    width: '100%',
                    fontSize: 13.5,
                    background: 'transparent',
                    color: 'var(--text-primary)'
                  }}
                />
                {fileSearch && (
                  <button 
                    onClick={() => setFileSearch('')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                  >
                    <MdClose />
                  </button>
                )}
              </div>

              {filesLoading ? (
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <div className="spinner" style={{ width: 30, height: 30 }} />
                  <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>Loading documents...</p>
                </div>
              ) : filteredFiles.length === 0 ? (
                <div className="card empty-state" style={{ padding: '60px 20px' }}>
                  <MdPictureAsPdf style={{ fontSize: 60, color: 'var(--text-muted)', opacity: 0.6 }} />
                  <h3 style={{ marginTop: 16 }}>No PDFs Uploaded</h3>
                  <p style={{ maxWidth: 400, margin: '8px auto 0', color: 'var(--text-secondary)' }}>
                    {fileSearch ? "No documents matches your search query." : "Upload employee handbooks, job requirements guides, interview rubrics or offer templates for quick access."}
                  </p>
                </div>
              ) : (
                /* Files List Card */
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                  <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Document Title</th>
                          <th>Original Filename</th>
                          <th>Size</th>
                          <th>Uploaded At</th>
                          <th style={{ textAlign: 'right' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredFiles.map((file) => (
                          <tr key={file.id}>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600 }}>
                                <MdPictureAsPdf style={{ color: 'var(--danger)', fontSize: 22, flexShrink: 0 }} />
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 300 }}>
                                  {file.title}
                                </span>
                              </div>
                            </td>
                            <td>
                              <span style={{ color: 'var(--text-secondary)', fontSize: 12, display: 'inline-block', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {file.filename}
                              </span>
                            </td>
                            <td>
                              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                {formatBytes(file.file_size || 0)}
                              </span>
                            </td>
                            <td>
                              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                {new Date(file.created_at).toLocaleDateString()}
                              </span>
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: 6 }}>
                                <button
                                  className="btn btn-outline btn-sm"
                                  onClick={() => {
                                    setViewPdfUrl(file.file_url);
                                    setViewPdfTitle(file.title);
                                  }}
                                  style={{ padding: '4px 10px', fontSize: 11.5 }}
                                >
                                  <MdVisibility /> View
                                </button>
                                <button
                                  className="btn btn-outline btn-sm"
                                  onClick={() => window.open(file.file_url, '_blank')}
                                  style={{ padding: '4px 10px', fontSize: 11.5 }}
                                >
                                  <MdOpenInNew /> Open
                                </button>
                                <button
                                  className="btn btn-outline btn-sm"
                                  onClick={() => deleteFile(file.id)}
                                  style={{ borderColor: 'var(--danger-light)', color: 'var(--danger)', padding: '4px 10px', fontSize: 11.5 }}
                                >
                                  <MdDelete /> Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Note Edit/Create Modal */}
      {showNoteModal && (
        <div className="modal-overlay" onClick={() => setShowNoteModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600, width: '90%' }}>
            <div className="modal-header">
              <h3 className="modal-title" style={{ fontSize: 16, fontWeight: 700 }}>
                {selectedNote ? 'Edit Workspace Note' : 'Create Workspace Note'}
              </h3>
              <button className="modal-close" onClick={() => setShowNoteModal(false)}>
                <MdClose />
              </button>
            </div>
            
            <form onSubmit={saveNote} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Note Title *</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. Technical Interview Rubric..."
                  value={noteForm.title}
                  onChange={(e) => setNoteForm(p => ({ ...p, title: e.target.value }))}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">Note Content *</label>
                <textarea
                  className="form-textarea"
                  required
                  rows={8}
                  placeholder="Write note contents here..."
                  value={noteForm.content}
                  onChange={(e) => setNoteForm(p => ({ ...p, content: e.target.value }))}
                  style={{ minHeight: 200 }}
                />
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowNoteModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Note
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View PDF Full-Overlay Modal */}
      {viewPdfUrl && (
        <div className="modal-overlay" onClick={() => setViewPdfUrl(null)}>
          <div 
            className="modal-box" 
            onClick={(e) => e.stopPropagation()} 
            style={{ 
              maxWidth: '85%', 
              width: '100%', 
              height: '90%', 
              display: 'flex', 
              flexDirection: 'column', 
              padding: 24 
            }}
          >
            <div className="modal-header" style={{ marginBottom: 16 }}>
              <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 16, fontWeight: 700 }}>
                <MdPictureAsPdf style={{ color: 'var(--danger)', fontSize: 22 }} />
                {viewPdfTitle}
              </h3>
              <div style={{ display: 'flex', gap: 10 }}>
                <button 
                  className="btn btn-outline btn-sm"
                  onClick={() => window.open(viewPdfUrl, '_blank')}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                >
                  <MdOpenInNew /> Open in New Tab
                </button>
                <button className="modal-close" onClick={() => setViewPdfUrl(null)}>
                  <MdClose />
                </button>
              </div>
            </div>
            
            <div style={{ flex: 1, background: '#f8fafc', borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              <iframe
                src={`${viewPdfUrl}#toolbar=1`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title={viewPdfTitle}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
