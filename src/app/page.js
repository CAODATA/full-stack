'use client';
import { useState } from 'react';

export default function Home() {
  const [links, setLinks] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chromeUserData, setChromeUserData] = useState('');
  const [chromeProfile, setChromeProfile] = useState('Default');
  const [maxComments, setMaxComments] = useState('');
  const [fbEmail, setFbEmail] = useState('');
  const [fbPassword, setFbPassword] = useState('');
  const [fbCookie, setFbCookie] = useState('');

  // Real-time link parsing
  const getLinkCounts = () => {
    const lines = links.split('\n').map(l => l.trim()).filter(l => l);
    let ytCount = 0;
    let fbCount = 0;
    for (const line of lines) {
      if (line.includes('youtube.com') || line.includes('youtu.be')) {
        ytCount++;
      } else if (line.includes('facebook.com') || line.includes('fb.watch') || line.includes('fb.com')) {
        fbCount++;
      }
    }
    return { ytCount, fbCount, total: lines.length };
  };

  const { ytCount, fbCount, total } = getLinkCounts();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!links.trim()) {
      setError('Vui lòng nhập ít nhất 1 đường link (YouTube hoặc Facebook).');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          links,
          chromeUserData,
          chromeProfile,
          maxComments,
          fbEmail,
          fbPassword,
          fbCookie
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Có lỗi xảy ra trong quá trình cào dữ liệu.');
      }

      // Trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'comments_crawl_clean.xlsx';
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
          <h1 style={styles.title}>Multi-Platform Comment Scraper</h1>
          <p style={styles.subtitle}>
            Dán danh sách link <b>YouTube</b> hoặc <b>Facebook</b> (mỗi link một dòng).
            Hệ thống tự động cào, phân loại comment/reply, làm sạch và xuất Excel.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.textareaWrapper}>
            <label style={styles.label}>Nhập danh sách đường dẫn liên kết:</label>
            <textarea
              style={styles.textarea}
              rows={8}
              placeholder="https://www.youtube.com/watch?v=8mhLfn5zdXE&#10;https://www.facebook.com/dongtaypromotion/posts/pfbid025...&#10;..."
              value={links}
              onChange={(e) => setLinks(e.target.value)}
            />
          </div>

          {/* Realtime link counter indicators */}
          {total > 0 && (
            <div style={styles.badgeContainer}>
              {ytCount > 0 && (
                <span style={styles.badgeYt}>
                  <span style={styles.badgeDotRed}></span>
                  YouTube ({ytCount})
                </span>
              )}
              {fbCount > 0 && (
                <span style={styles.badgeFb}>
                  <span style={styles.badgeDotBlue}></span>
                  Facebook ({fbCount})
                </span>
              )}
              {ytCount === 0 && fbCount === 0 && (
                <span style={styles.badgeWarning}>
                  ⚠️ Định dạng link chưa được hỗ trợ
                </span>
              )}
            </div>
          )}

          {/* Số lượng cmt */}
          <div style={styles.inputGroup}>
            <label style={styles.label}>Số lượng bình luận tối đa mỗi link:</label>
            <input
              type="number"
              value={maxComments}
              onChange={(e) => setMaxComments(e.target.value)}
              style={styles.input}
              placeholder="Để trống để cào tất cả (hoặc điền số cụ thể: 50, 500, 1000...)"
              min="1"
            />
          </div>

          {fbCount > 0 && (
            <div style={styles.inputGroup}>
              <label style={styles.label}>
                Facebook Cookie (Tùy chọn):
                <span style={{ fontSize: '0.8rem', fontWeight: 'normal', color: '#94a3b8', marginLeft: '0.5rem' }}>
                  (Khuyên dùng: Dán cookie để bỏ qua Email/Mật khẩu và vượt qua xác thực 2 lớp - 2FA)
                </span>
              </label>
              <textarea
                style={{ ...styles.textarea, height: '80px', fontFamily: 'monospace', fontSize: '0.85rem' }}
                placeholder="Ví dụ: sb=xxxx; datr=xxxx; c_user=xxxx; xs=xxxx; ..."
                value={fbCookie}
                onChange={(e) => setFbCookie(e.target.value)}
              />
            </div>
          )}

          {fbCount > 0 && (
            <div style={styles.noticeCard}>
              <p style={styles.noticeTitle}>⚠️ Lưu ý cào Facebook:</p>
              <p style={styles.noticeText}>
                Bạn cần <b>đóng hoàn toàn tất cả cửa sổ trình duyệt Chrome thường</b> đang mở trên máy tính trước khi bấm nút cào để tránh lỗi xung đột profile Chrome.
              </p>
            </div>
          )}

          {error && (
            <div style={styles.error}>
              <div>{error}</div>
              {fbCount > 0 && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#fca5a5', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <div>
                    💡 <b>Trạng thái xác thực (Passkey/2FA):</b>{' '}
                    <a
                      href="/api/login-error-screenshot?type=verification"
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#93c5fd', textDecoration: 'underline', fontWeight: 'bold' }}
                    >
                      Xem ảnh chụp màn hình 2FA
                    </a>
                    {' | '}
                    <a
                      href="/api/login-error-html?type=verification"
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#93c5fd', textDecoration: 'underline', fontWeight: 'bold' }}
                    >
                      Xem mã nguồn HTML 2FA
                    </a>
                  </div>
                  <div>
                    💡 <b>Trạng thái cuối cùng của trình duyệt:</b>{' '}
                    <a
                      href="/api/login-error-screenshot"
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#93c5fd', textDecoration: 'underline', fontWeight: 'bold' }}
                    >
                      Xem ảnh chụp màn hình Chrome
                    </a>
                    {' | '}
                    <a
                      href="/api/login-error-html"
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#93c5fd', textDecoration: 'underline', fontWeight: 'bold' }}
                    >
                      Xem mã nguồn HTML Chrome
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
            disabled={loading}
          >
            {loading ? (
              <span style={styles.loadingText}>
                <span className="spinner" style={styles.spinner}></span>
                {fbCount > 0
                  ? 'Đang mở Chrome để cào Facebook... (có thể mất vài phút)'
                  : 'Đang xử lý dữ liệu...'}
              </span>
            ) : (
              'Bắt đầu Cào Dữ Liệu & Tải Excel'
            )}
          </button>
        </form>
      </div>

      {/* Basic inline keyframes for spinner */}
      <style dangerouslySetInnerHTML={{
        __html: `
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
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid var(--border)',
    borderRadius: '24px',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '750px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
  },
  header: {
    textAlign: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2.2rem',
    fontWeight: '800',
    background: 'linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    marginBottom: '0.75rem',
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: '1rem',
    lineHeight: '1.6',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  textareaWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  label: {
    fontSize: '0.95rem',
    fontWeight: '600',
    color: '#e2e8f0',
  },
  labelSub: {
    fontSize: '0.9rem',
    color: '#cbd5e1',
  },
  textarea: {
    width: '100%',
    backgroundColor: 'rgba(15, 23, 42, 0.7)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '1.25rem',
    color: '#fff',
    fontSize: '0.95rem',
    fontFamily: 'monospace',
    lineHeight: '1.6',
    resize: 'vertical',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  },
  badgeContainer: {
    display: 'flex',
    gap: '0.75rem',
    flexWrap: 'wrap',
    padding: '0.25rem 0',
  },
  badgeYt: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    color: '#fca5a5',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '99px',
    padding: '0.4rem 1rem',
    fontSize: '0.85rem',
    fontWeight: '600',
  },
  badgeDotRed: {
    width: '8px',
    height: '8px',
    backgroundColor: '#ef4444',
    borderRadius: '50%',
  },
  badgeFb: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    color: '#93c5fd',
    border: '1px solid rgba(59, 130, 246, 0.3)',
    borderRadius: '99px',
    padding: '0.4rem 1rem',
    fontSize: '0.85rem',
    fontWeight: '600',
  },
  badgeDotBlue: {
    width: '8px',
    height: '8px',
    backgroundColor: '#3b82f6',
    borderRadius: '50%',
  },
  badgeWarning: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    color: '#fde047',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    borderRadius: '99px',
    padding: '0.4rem 1rem',
    fontSize: '0.85rem',
    fontWeight: '600',
  },
  advancedWrapper: {
    border: '1px solid var(--border)',
    borderRadius: '12px',
    overflow: 'hidden',
    backgroundColor: 'rgba(30, 41, 59, 0.4)',
  },
  advancedToggle: {
    width: '100%',
    padding: '1rem 1.25rem',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#cbd5e1',
    fontSize: '0.95rem',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    textAlign: 'left',
  },
  advancedContent: {
    padding: '0 1.25rem 1.25rem 1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    borderTop: '1px solid var(--border)',
    paddingTop: '1.25rem',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
  },
  input: {
    backgroundColor: 'rgba(15, 23, 42, 0.7)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    padding: '0.75rem 1rem',
    color: '#fff',
    fontSize: '0.9rem',
    outline: 'none',
  },
  noticeCard: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    border: '1px solid rgba(245, 158, 11, 0.25)',
    borderRadius: '8px',
    padding: '1rem',
  },
  noticeTitle: {
    color: '#fef08a',
    fontWeight: '700',
    fontSize: '0.9rem',
    marginBottom: '0.35rem',
  },
  noticeText: {
    color: '#fef08a',
    fontSize: '0.85rem',
    lineHeight: '1.5',
  },
  error: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    padding: '1rem',
    borderRadius: '12px',
    fontSize: '0.95rem',
  },
  button: {
    backgroundColor: 'var(--primary)',
    color: '#fff',
    border: 'none',
    padding: '1.2rem',
    borderRadius: '12px',
    fontSize: '1.05rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s, transform 0.1s',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.35)',
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
    textAlign: 'center',
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
