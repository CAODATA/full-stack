'use client';
import { useState } from 'react';

export default function Home() {
  const [links, setLinks] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!links.trim()) {
      setError('Vui lòng nhập ít nhất 1 link YouTube.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ links })
      });

      if (!response.ok) {
        throw new Error('Có lỗi xảy ra trong quá trình cào dữ liệu.');
      }

      // Trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'tat_ca_comments_clean.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={styles.main}>
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>YouTube Comment Scraper</h1>
          <p style={styles.subtitle}>
            Dán link YouTube (mỗi link 1 dòng). Hệ thống sẽ tự động cào, làm sạch và trả về file Excel chuẩn gọn gàng.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <textarea
            style={styles.textarea}
            rows={8}
            placeholder="https://youtu.be/8mhLfn5zdXE&#10;https://youtu.be/f5ZzYyEgb14&#10;..."
            value={links}
            onChange={(e) => setLinks(e.target.value)}
          />
          
          {error && <div style={styles.error}>{error}</div>}

          <button 
            type="submit" 
            style={{...styles.button, ...(loading ? styles.buttonDisabled : {})}}
            disabled={loading}
          >
            {loading ? (
              <span style={styles.loadingText}>
                <span className="spinner" style={styles.spinner}></span>
                Đang xử lý... (Có thể mất vài phút)
              </span>
            ) : (
              'Bắt đầu Cào Dữ Liệu & Tải Excel'
            )}
          </button>
        </form>
      </div>

      {/* Basic inline keyframes for spinner */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}} />
    </main>
  );
}

const styles = {
  main: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
  },
  container: {
    backgroundColor: 'var(--card-bg)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    border: '1px solid var(--border)',
    borderRadius: '24px',
    padding: '3rem',
    width: '100%',
    maxWidth: '700px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
  },
  header: {
    textAlign: 'center',
    marginBottom: '2.5rem',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: '800',
    background: 'linear-gradient(to right, #60a5fa, #a78bfa, #f472b6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    marginBottom: '1rem',
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: '1.1rem',
    lineHeight: '1.6',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  textarea: {
    width: '100%',
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '1.5rem',
    color: '#fff',
    fontSize: '1rem',
    fontFamily: 'monospace',
    lineHeight: '1.5',
    resize: 'vertical',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  },
  error: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    padding: '1rem',
    borderRadius: '8px',
    fontSize: '0.95rem',
  },
  button: {
    backgroundColor: 'var(--primary)',
    color: '#fff',
    border: 'none',
    padding: '1.25rem',
    borderRadius: '12px',
    fontSize: '1.1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s, transform 0.1s',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.39)',
  },
  buttonDisabled: {
    backgroundColor: '#475569',
    cursor: 'not-allowed',
    boxShadow: 'none',
  },
  loadingText: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  spinner: {
    display: 'inline-block',
    width: '20px',
    height: '20px',
    border: '3px solid rgba(255,255,255,0.3)',
    borderRadius: '50%',
    borderTopColor: '#fff',
    animation: 'spin 1s ease-in-out infinite',
  }
};
