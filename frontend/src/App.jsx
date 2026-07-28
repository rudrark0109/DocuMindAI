import React, { useEffect, useMemo, useRef, useState } from "react";
import { deleteDocument, getDocumentStatus, renameDocument, retryDocumentProcessing, uploadDocument } from "./services/documentApi";

const DEMO_USER = {
  username: "admin1",
  password: "docmind@123",
  displayName: "Admin One",
};

const DEMO_FILES = [
  {
    id: "demo-1",
    name: "Q4 product strategy.pdf",
    type: "PDF",
    size: "3.8 MB",
    sizeBytes: 3984588,
    words: 18420,
    tokens: 24180,
    status: "Ready",
    updatedAt: "2026-07-25T14:16:00",
    owner: "admin1",
  },
  {
    id: "demo-2",
    name: "Customer interview notes.pdf",
    type: "PDF",
    size: "1.2 MB",
    sizeBytes: 1258291,
    words: 7680,
    tokens: 10120,
    status: "Ready",
    updatedAt: "2026-07-23T09:42:00",
    owner: "admin1",
  },
  {
    id: "demo-3",
    name: "Engineering handbook.pdf",
    type: "PDF",
    size: "8.6 MB",
    sizeBytes: 9019431,
    words: 43200,
    tokens: 58600,
    status: "Ready",
    updatedAt: "2026-07-20T16:08:00",
    owner: "admin1",
  },
  {
    id: "demo-4",
    name: "Brand voice & messaging.pdf",
    type: "PDF",
    size: "2.1 MB",
    sizeBytes: 2202009,
    words: 11240,
    tokens: 15100,
    status: "Ready",
    updatedAt: "2026-07-18T11:24:00",
    owner: "admin1",
  },
  {
    id: "demo-5",
    name: "2026 planning brief.pdf",
    type: "PDF",
    size: "4.4 MB",
    sizeBytes: 4613734,
    words: 22700,
    tokens: 29900,
    status: "Processing",
    updatedAt: "2026-07-16T13:51:00",
    owner: "admin1",
  },
];

const fileKey = (username) => `documind_files_${username}`;
const userKey = "documind_users";

function readStorage(key, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // The dashboard still works for the current session if storage is unavailable.
  }
}

function Icon({ name, size = 18, stroke = 1.8 }) {
  const paths = {
    search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></>,
    upload: <><path d="M12 16V4" /><path d="m7 9 5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></>,
    file: <><path d="M6 2.8h8l4 4V21H6a2 2 0 0 1-2-2V4.8a2 2 0 0 1 2-2Z" /><path d="M14 3v5h5M8 13h8M8 17h5" /></>,
    grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    list: <><path d="M8 6h12M8 12h12M8 18h12" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
    eye: <><path d="M2.5 12s3.5-5 9.5-5 9.5 5 9.5 5-3.5 5-9.5 5-9.5-5-9.5-5Z" /><circle cx="12" cy="12" r="2" /></>,
    eyeOff: <><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8" /><path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6 0 9.5 7 9.5 7a17 17 0 0 1-3.1 3.8M6.3 6.4C3.8 8.1 2.5 12 2.5 12S6 19 12 19c1 0 1.9-.2 2.7-.5" /></>,
    dots: <><circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" /></>,
    rename: <><path d="m4 20 4.2-1 10.6-10.6a2 2 0 0 0-2.8-2.8L5.4 16.2 4 20Z" /><path d="m14.5 7.1 2.8 2.8" /></>,
    trash: <><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6" /></>,
    logout: <><path d="M10 5H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h5" /><path d="M14 8l4 4-4 4M18 12H8" /></>,
    spark: <><path d="m12 3 1.4 5.6L19 10l-5.6 1.4L12 17l-1.4-5.6L5 10l5.6-1.4L12 3ZM19 17l.5 2.5L22 20l-2.5.5L19 23l-.5-2.5L16 20l2.5-.5L19 17Z" /></>,
  };

  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function formatDate(date) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(date));
}

function formatNumber(value) {
  return new Intl.NumberFormat("en", { notation: value > 999999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value);
}

function passwordIsValid(password) {
  return /[A-Za-z]/.test(password) && /\d/.test(password) && /[^A-Za-z\d]/.test(password);
}

function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("admin1");
  const [password, setPassword] = useState("docmind@123");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  function submit(event) {
    event.preventDefault();
    const cleanUsername = username.trim().toLowerCase();
    const users = readStorage(userKey, [DEMO_USER]);
    if (!cleanUsername || !password) {
      setError("Enter both your username and password.");
      return;
    }
    if (mode === "create") {
      if (!passwordIsValid(password)) {
        setError("Use at least one letter, one number, and one symbol.");
        return;
      }
      if (users.some((user) => user.username === cleanUsername)) {
        setError("That username is already in use.");
        return;
      }
      const newUser = { username: cleanUsername, password, displayName: cleanUsername };
      writeStorage(userKey, [...users, newUser]);
      onLogin(newUser);
      return;
    }
    const user = users.find((candidate) => candidate.username === cleanUsername && candidate.password === password);
    if (!user) {
      setError("Username or password is incorrect.");
      return;
    }
    onLogin(user);
  }

  return (
    <div className="auth-layout">
      <div className="auth-decoration">
        <div className="glow glow-one" />
        <div className="glow glow-two" />
        <div className="auth-mark"><span>DM</span></div>
        <p className="eyebrow light">Your private knowledge base</p>
        <h1>Make every document<br /><em>more useful.</em></h1>
        <p className="auth-intro">Bring your files together, turn them into searchable knowledge, and keep your work exactly where it belongs: with you.</p>
        <div className="auth-perks"><span><Icon name="check" size={15} /> Local-first access</span><span><Icon name="check" size={15} /> Private by account</span></div>
      </div>
      <div className="auth-panel">
        <div className="mobile-brand"><span className="brand-symbol">DM</span><span>DocuMind</span></div>
        <div className="auth-form-wrap">
          <p className="eyebrow">Welcome to DocuMind</p>
          <h2>{mode === "login" ? "Sign in to your workspace" : "Create a local account"}</h2>
          <p className="muted">{mode === "login" ? "Your files and search results stay scoped to this account." : "Set up a private workspace on this device."}</p>
          <form onSubmit={submit} className="auth-form">
            <label>Username<input value={username} onChange={(event) => { setUsername(event.target.value); setError(""); }} placeholder="e.g. alex" autoComplete="username" /></label>
            <label>Password<div className="password-field"><input type={showPassword ? "text" : "password"} value={password} onChange={(event) => { setPassword(event.target.value); setError(""); }} placeholder="Your password" autoComplete={mode === "login" ? "current-password" : "new-password"} /><button type="button" className="icon-button password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"}><Icon name={showPassword ? "eyeOff" : "eye"} size={17} /></button></div></label>
            {mode === "create" && <p className={`password-hint ${passwordIsValid(password) ? "valid" : ""}`}><Icon name={passwordIsValid(password) ? "check" : "lock"} size={14} /> At least one letter, number, and symbol</p>}
            {error && <div className="form-error">{error}</div>}
            <button type="submit" className="primary-button auth-submit">{mode === "login" ? "Sign in" : "Create account"}<span>→</span></button>
          </form>
          <div className="auth-switch">{mode === "login" ? "New to DocuMind?" : "Already have an account?"}<button type="button" onClick={() => { setMode(mode === "login" ? "create" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "Sign in instead"}</button></div>
          {mode === "login" && <div className="demo-note"><span className="demo-dot" /><div><strong>Demo account ready</strong><span>admin1 · docmind@123</span></div><button type="button" onClick={() => { setUsername("admin1"); setPassword("docmind@123"); setError(""); }}>Use demo</button></div>}
        </div>
        <p className="auth-footer">Local authenticator · No external account required</p>
      </div>
    </div>
  );
}

function Stats({ files }) {
  const words = files.reduce((sum, file) => sum + (file.words || 0), 0);
  const tokens = files.reduce((sum, file) => sum + (file.tokens || 0), 0);
  const bytes = files.reduce((sum, file) => sum + (file.sizeBytes || 0), 0);
  const stats = [
    { label: "Vector words", value: formatNumber(words), detail: "Indexed and ready", icon: "spark", color: "violet" },
    { label: "Tokens processed", value: formatNumber(tokens), detail: "Across your files", icon: "file", color: "blue" },
    { label: "Storage used", value: `${(bytes / (1024 ** 3)).toFixed(2)} GB`, detail: "of 10 GB available", icon: "grid", color: "orange", progress: Math.min((bytes / (10 * 1024 ** 3)) * 100, 100) },
  ];
  return <section className="stats-section"><div className="content-width stats-grid">{stats.map((stat) => <div className="stat-card" key={stat.label}><div className={`stat-icon ${stat.color}`}><Icon name={stat.icon} size={18} /></div><div className="stat-copy"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.detail}</small>{stat.progress !== undefined && <div className="progress-track"><span style={{ width: `${Math.max(stat.progress, 2)}%` }} /></div>}</div></div>)}</div></section>;
}

function UploadModal({ onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);

  function selectFile(event) {
    const nextFile = event.target.files?.[0];
    if (nextFile) { setFile(nextFile); setMessage(""); }
  }

  async function submit() {
    if (!file) { setMessage("Choose a PDF to continue."); return; }
    setIsUploading(true);
    try {
      const result = await uploadDocument(file);
      const uploaded = {
        id: result.id,
        name: result.original_filename,
        type: "PDF",
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        sizeBytes: file.size,
        words: 0,
        tokens: 0,
        status: "Queued",
        processingStage: result.processing_stage,
        progress: result.processing_progress,
        processingError: null,
        updatedAt: new Date().toISOString(),
      };
      onUploaded(uploaded);
    } catch (error) {
      setMessage(error.message || "The upload could not be queued.");
      setIsUploading(false);
      return;
    }
    setIsUploading(false);
  }

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><div className="modal-header"><div><p className="eyebrow">Add to your library</p><h2 id="upload-title">Upload a document</h2></div><button className="icon-button" onClick={onClose} aria-label="Close upload dialog"><Icon name="close" /></button></div><button className={`drop-zone ${file ? "has-file" : ""}`} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const dropped = event.dataTransfer.files?.[0]; if (dropped) { setFile(dropped); setMessage(""); } }}><span className="drop-icon"><Icon name={file ? "file" : "upload"} size={24} /></span><strong>{file ? file.name : "Drop a PDF here or browse"}</strong><span>{file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · Ready to upload` : "PDF files up to 25 MB"}</span><input ref={inputRef} type="file" accept="application/pdf,.pdf" onChange={selectFile} hidden /></button>{message && <div className="form-error">{message}</div>}<div className="modal-actions"><button className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" onClick={submit} disabled={isUploading}>{isUploading ? "Uploading…" : "Upload"}<span>→</span></button></div></div></div>;
}

function FileRow({ file, onMenu }) {
  const statusDetail = ["Queued", "Processing"].includes(file.status) ? ` · ${file.progress || 0}%` : "";
  const statusClass = file.status === "Ready" ? "ready" : file.status === "Failed" ? "failed" : "processing";
  return <div className="file-row"><div className="file-name-cell"><span className="file-type-icon"><Icon name="file" size={17} /></span><div><strong>{file.name}</strong><span>PDF document</span></div></div><div className="file-status"><span className={`status-dot ${statusClass}`} />{file.status}{statusDetail}</div><div className="file-meta">{file.size}</div><div className="file-meta">{formatDate(file.updatedAt)}</div><button className="icon-button row-menu" onClick={() => onMenu(file)} aria-label={`More options for ${file.name}`}><Icon name="dots" /></button></div>;
}

function FileActionsModal({ file, onClose, onRename, onDelete, onRetry }) {
  const [filename, setFilename] = useState(file.name);
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");

  async function submitRename(event) {
    event.preventDefault();
    const cleaned = filename.trim();
    const pdfName = cleaned.toLowerCase().endsWith(".pdf") ? cleaned : `${cleaned}.pdf`;
    if (!cleaned) { setMessage("Enter a filename."); return; }
    setBusyAction("rename");
    setMessage("");
    try {
      await onRename(file, pdfName);
      onClose();
    } catch (error) {
      setMessage(error.message || "Could not rename the document.");
      setBusyAction("");
    }
  }

  async function removeFile() {
    if (!window.confirm(`Delete “${file.name}”? This cannot be undone.`)) return;
    setBusyAction("delete");
    setMessage("");
    try {
      await onDelete(file);
      onClose();
    } catch (error) {
      setMessage(error.message || "Could not delete the document.");
      setBusyAction("");
    }
  }

  async function retryProcessing() {
    setBusyAction("retry");
    setMessage("");
    try {
      await onRetry(file);
      onClose();
    } catch (error) {
      setMessage(error.message || "Could not retry processing.");
      setBusyAction("");
    }
  }

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busyAction) onClose(); }}><div className="modal file-actions-modal" role="dialog" aria-modal="true" aria-labelledby="file-actions-title"><div className="modal-header"><div><p className="eyebrow">File options</p><h2 id="file-actions-title">Manage document</h2></div><button className="icon-button" onClick={onClose} disabled={Boolean(busyAction)} aria-label="Close file options"><Icon name="close" /></button></div><form onSubmit={submitRename}><label className="filename-label">Filename<input value={filename} onChange={(event) => { setFilename(event.target.value); setMessage(""); }} maxLength={255} autoFocus /></label>{file.processingError && <p className="processing-error">{file.processingError}</p>}{message && <div className="form-error">{message}</div>}<div className="modal-actions split-actions"><button type="button" className="danger-button" onClick={removeFile} disabled={Boolean(busyAction)}><Icon name="trash" size={15} />{busyAction === "delete" ? "Deleting…" : "Delete"}</button><div>{file.status === "Failed" && <button type="button" className="secondary-button" onClick={retryProcessing} disabled={Boolean(busyAction)}>{busyAction === "retry" ? "Retrying…" : "Retry processing"}</button>}<button type="button" className="secondary-button" onClick={onClose} disabled={Boolean(busyAction)}>Cancel</button><button type="submit" className="primary-button" disabled={Boolean(busyAction) || filename.trim() === file.name}><Icon name="rename" size={15} />{busyAction === "rename" ? "Renaming…" : "Rename"}</button></div></div></form></div></div>;
}

function Dashboard({ user, onLogout }) {
  const [files, setFiles] = useState(() => {
    const stored = readStorage(fileKey(user.username), null);
    return stored || (user.username === "admin1" ? DEMO_FILES : []);
  });
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState("All files");
  const [view, setView] = useState("list");
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const searchRef = useRef(null);

  useEffect(() => writeStorage(fileKey(user.username), files), [files, user.username]);
  useEffect(() => { if (searchOpen) searchRef.current?.focus(); }, [searchOpen]);
  useEffect(() => {
    const pendingFiles = files.filter((file) => !file.id.startsWith("demo-") && !file.id.startsWith("local-") && ["Queued", "Processing"].includes(file.status));
    if (!pendingFiles.length) return undefined;

    let cancelled = false;
    async function refreshStatuses() {
      const results = await Promise.allSettled(pendingFiles.map(async (file) => ({ id: file.id, status: await getDocumentStatus(file.id) })));
      if (cancelled) return;
      const updates = new Map(results.filter((result) => result.status === "fulfilled").map((result) => [result.value.id, result.value.status]));
      if (!updates.size) return;
      setFiles((current) => current.map((file) => {
        const status = updates.get(file.id);
        if (!status) return file;
        const displayStatus = status.job_status === "completed" ? "Ready" : status.job_status === "failed" ? "Failed" : status.job_status === "queued" ? "Queued" : "Processing";
        if (file.status === displayStatus && file.progress === status.progress && file.processingStage === status.stage && file.processingError === status.error) return file;
        return { ...file, status: displayStatus, progress: status.progress, processingStage: status.stage, processingError: status.error, updatedAt: status.updated_at || new Date().toISOString() };
      }));
    }

    refreshStatuses();
    const interval = window.setInterval(refreshStatuses, 2000);
    return () => { cancelled = true; window.clearInterval(interval); };
  }, [files]);

  const visibleFiles = useMemo(() => {
    const lowerQuery = query.trim().toLowerCase();
    return files.filter((file) => {
      const matchesQuery = !lowerQuery || file.name.toLowerCase().includes(lowerQuery);
      const matchesTab = activeTab === "All files" || (activeTab === "PDFs" && file.type === "PDF") || (activeTab === "Recent" && Date.now() - new Date(file.updatedAt).getTime() < 14 * 86400000);
      return matchesQuery && matchesTab && file.owner === user.username;
    });
  }, [files, query, activeTab]);

  function addFile(uploaded) {
    const ownedFile = { ...uploaded, owner: user.username };
    setFiles((current) => [ownedFile, ...current]);
    setShowUpload(false);
  }

  async function renameFile(file, filename) {
    if (!file.id.startsWith("demo-") && !file.id.startsWith("local-")) {
      await renameDocument(file.id, filename);
    }
    setFiles((current) => current.map((item) => item.id === file.id ? { ...item, name: filename, updatedAt: new Date().toISOString() } : item));
  }

  async function removeFile(file) {
    if (!file.id.startsWith("demo-") && !file.id.startsWith("local-")) {
      await deleteDocument(file.id);
    }
    setFiles((current) => current.filter((item) => item.id !== file.id));
  }

  async function retryFile(file) {
    if (file.id.startsWith("demo-") || file.id.startsWith("local-")) return;
    const status = await retryDocumentProcessing(file.id);
    setFiles((current) => current.map((item) => item.id === file.id ? { ...item, status: "Queued", progress: status.progress, processingStage: status.stage, processingError: null, updatedAt: new Date().toISOString() } : item));
  }

  return <div className="app-shell"><header className="topbar"><div className="topbar-inner content-width"><div className="brand"><span className="brand-symbol">DM</span><span>DocuMind</span></div><div className="topbar-actions"><button className="toolbar-button" onClick={() => setShowUpload(true)}><Icon name="upload" size={17} /><span>Upload</span></button><button className={`toolbar-button ${searchOpen ? "active" : ""}`} onClick={() => setSearchOpen((open) => !open)}><Icon name="search" size={17} /><span>Search</span></button><div className="profile-wrap"><button className="profile-button" onClick={() => setProfileOpen((open) => !open)}><span className="avatar">{user.username.slice(0, 2).toUpperCase()}</span><span className="profile-name">{user.username}</span><span className="chevron">⌄</span></button>{profileOpen && <div className="profile-menu"><div className="profile-menu-head"><span className="avatar large">{user.username.slice(0, 2).toUpperCase()}</span><div><strong>{user.displayName || user.username}</strong><span>@{user.username}</span></div></div><div className="menu-divider" /><button onClick={onLogout}><Icon name="logout" size={16} /> Sign out</button></div>}</div></div></div>{searchOpen && <div className="search-bar-wrap content-width"><div className="search-bar"><Icon name="search" size={17} /><input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search your documents…" /><kbd>ESC</kbd>{query && <button className="icon-button" onClick={() => setQuery("")} aria-label="Clear search"><Icon name="close" size={16} /></button>}</div></div>}</header><main><section className="hero content-width"><div><p className="eyebrow">Private workspace</p><h1>Good morning, {user.displayName?.split(" ")[0] || user.username}</h1><p className="hero-subtitle">Your documents, indexed and ready to explore.</p></div><button className="primary-button hero-upload" onClick={() => setShowUpload(true)}><Icon name="upload" size={17} /> Upload document</button></section><Stats files={files} /><section className="library-section content-width"><div className="library-header"><div><p className="eyebrow">Document library</p><h2>Your files <span>{files.length}</span></h2></div><div className="view-controls"><button className={view === "list" ? "selected" : ""} onClick={() => setView("list")} aria-label="List view"><Icon name="list" size={18} /></button><button className={view === "grid" ? "selected" : ""} onClick={() => setView("grid")} aria-label="Grid view"><Icon name="grid" size={17} /></button></div></div><div className="library-toolbar"><div className="tabs">{["All files", "Recent", "PDFs"].map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div><span className="scope-label"><span className="scope-icon"><Icon name="lock" size={13} /></span> Only you can see these files</span></div>{visibleFiles.length ? <div className={view === "grid" ? "file-grid" : "file-list"}>{view === "list" && <div className="file-list-head"><span>Name</span><span>Status</span><span>Size</span><span>Last updated</span><span /></div>}{visibleFiles.map((file) => view === "list" ? <FileRow key={file.id} file={file} onMenu={setSelectedFile} /> : <div className="file-card" key={file.id}><div className="file-card-top"><span className="file-type-icon"><Icon name="file" size={20} /></span><button className="icon-button" onClick={() => setSelectedFile(file)} aria-label={`More options for ${file.name}`}><Icon name="dots" /></button></div><strong>{file.name}</strong><span className="file-card-size">{file.size} · {formatDate(file.updatedAt)}</span><span className="card-status"><span className={`status-dot ${file.status === "Ready" ? "ready" : file.status === "Failed" ? "failed" : "processing"}`} />{file.status}{["Queued", "Processing"].includes(file.status) ? ` · ${file.progress || 0}%` : ""}</span></div>)}</div> : <div className="empty-state"><span className="empty-icon"><Icon name="search" size={24} /></span><h3>{query ? "No matching files" : "Your library is empty"}</h3><p>{query ? "Try a different name or clear your search." : "Upload your first document to start building your private knowledge base."}</p>{!query && <button className="primary-button" onClick={() => setShowUpload(true)}>Upload a document <span>→</span></button>}</div>}<div className="library-footer"><span>Showing {visibleFiles.length} of {files.length} files</span><span>Files are private to <strong>@{user.username}</strong></span></div></section></main>{showUpload && <UploadModal onClose={() => setShowUpload(false)} onUploaded={addFile} />}{selectedFile && <FileActionsModal file={selectedFile} onClose={() => setSelectedFile(null)} onRename={renameFile} onDelete={removeFile} onRetry={retryFile} />}</div>;
}

function App() {
  const [user, setUser] = useState(() => readStorage("documind_current_user", null));

  function login(nextUser) {
    setUser(nextUser);
    writeStorage("documind_current_user", nextUser);
  }

  function logout() {
    setUser(null);
    try { window.localStorage.removeItem("documind_current_user"); } catch { /* no-op */ }
  }

  return user ? <Dashboard user={user} onLogout={logout} /> : <AuthScreen onLogin={login} />;
}

export default App;
