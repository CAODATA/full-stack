import os
import sys
import time
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

def init_driver(user_data_dir, profile_name):
    opts = Options()
    if user_data_dir:
        opts.add_argument(f"--user-data-dir={user_data_dir}")
    if profile_name:
        opts.add_argument(f"--profile-directory={profile_name}")
    
    import sys
    if sys.platform != "win32":
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )
    return driver

def expand_comments(driver, max_comments):
    logger.info("⏳ Đang chuyển chế độ xem bình luận sang 'Tất cả bình luận' (All comments)...")
    try:
        filter_button = None
        for xpath in [
            "//span[contains(text(), 'Phù hợp nhất') or contains(text(), 'Xem nhiều nhất') or contains(text(), 'Most relevant') or contains(text(), 'Top comments')]",
            "//div[@role='button']//span[contains(text(), 'Phù hợp nhất') or contains(text(), 'Most relevant')]"
        ]:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        filter_button = el
                        break
                if filter_button:
                    break
            except Exception:
                continue

        if filter_button:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", filter_button)
            time.sleep(1.5)
            
            all_comments_option = None
            for xpath in [
                "//span[contains(text(), 'Tất cả bình luận') or contains(text(), 'All comments')]",
                "//div[@role='menuitem']//span[contains(text(), 'Tất cả') or contains(text(), 'All')]"
            ]:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            all_comments_option = el
                            break
                    if all_comments_option:
                        break
                except Exception:
                    continue
            
            if all_comments_option:
                driver.execute_script("arguments[0].click();", all_comments_option)
                logger.info("✅ Đã chuyển sang chế độ 'Tất cả bình luận'")
                time.sleep(3.0)
    except Exception as e:
        logger.warning(f"⚠️ Không thể chuyển sang chế độ 'Tất cả bình luận': {e}")

    logger.info("⏳ Bắt đầu mở rộng danh sách bình luận...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    comment_click_count = 0
    while comment_click_count < 100:
        try:
            buttons = driver.find_elements(By.XPATH, 
                "//span[contains(text(), 'Xem thêm bình luận') or contains(text(), 'Xem các bình luận trước') or contains(text(), 'View more comments') or contains(text(), 'View previous comments') or contains(text(), 'Xem bình luận khác') or contains(text(), 'View more replies')]"
            )
            if not buttons:
                break
            
            clicked = False
            for btn in buttons:
                try:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        comment_click_count += 1
                        time.sleep(2.0)
                        break
                except Exception:
                    continue
            if not clicked:
                break
        except Exception as e:
            logger.warning(f"Lỗi khi bấm 'Xem thêm bình luận': {e}")
            break

    logger.info(f"✅ Đã bấm 'Xem thêm bình luận' {comment_click_count} lần.")

    logger.info("⏳ Bắt đầu mở rộng các phản hồi (replies)...")
    reply_click_count = 0
    while reply_click_count < 100:
        try:
            reply_buttons = driver.find_elements(By.XPATH,
                "//span[contains(text(), 'phản hồi') or contains(text(), 'replies') or contains(text(), 'phản hồi khác') or contains(text(), 'replies other')]"
            )
            clicked = False
            for btn in reply_buttons:
                try:
                    text = btn.text.strip().lower()
                    if btn.is_displayed() and ('xem' in text or 'view' in text or any(char.isdigit() for char in text)):
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        reply_click_count += 1
                        time.sleep(1.5)
                        break
                except Exception:
                    continue
            if not clicked:
                break
        except Exception as e:
            logger.warning(f"Lỗi khi bấm mở rộng phản hồi: {e}")
            break
            
    logger.info(f"✅ Đã bấm mở rộng phản hồi {reply_click_count} lần.")

def parse_comments(html_content, post_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = []
    
    article_tags = soup.find_all(attrs={"role": "article"})
    seen_comments = set()
    
    for comment_el in article_tags:
        label = (comment_el.get('aria-label') or '').lower()
        if not any(x in label for x in ['bình luận', 'phản hồi', 'comment', 'reply']):
            continue
            
        # Find author name
        author_name = None
        links = comment_el.find_all('a')
        for link in links:
            # Ensure this link is directly inside this comment, not in a nested comment
            parent_comment = link.find_parent(attrs={"role": "article"})
            if parent_comment != comment_el:
                continue
            name = link.get_text().strip()
            if name and len(name) >= 2 and '\n' not in name and name not in ['Thích', 'Like', 'Phản hồi', 'Reply', 'Chia sẻ', 'Share']:
                author_name = name
                break
                
        if not author_name:
            continue
            
        # Find text content
        comment_text = None
        dir_auto_tags = comment_el.find_all(lambda tag: tag.name in ['div', 'span'] and tag.get('dir') == 'auto')
        for tag in dir_auto_tags:
            # Ensure it is directly inside this comment
            if tag.find_parent(attrs={"role": "article"}) != comment_el:
                continue
            # Ensure it is not inside an anchor tag (author name)
            if tag.find_parent('a'):
                continue
            val = tag.get_text().strip()
            if val:
                comment_text = val
                break
                
        if not comment_text:
            continue
            
        unique_key = f"{author_name}|{comment_text[:100]}"
        if unique_key in seen_comments:
            continue
        seen_comments.add(unique_key)
        
        # Likes count
        likes = 0
        reaction_els = comment_el.find_all(lambda tag: tag.name in ['div', 'span'] and tag.get('aria-label') and any(x in tag.get('aria-label').lower() for x in ['thích', 'like', 'reaction', 'bày tỏ']))
        for rx in reaction_els:
            rx_text = rx.get_text().strip()
            if rx_text.isdigit():
                likes = int(rx_text)
                break
                
        published_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        comments.append({
            "video_id": post_url,
            "type": "comment",
            "author": author_name,
            "text": comment_text,
            "likes": likes,
            "published_at": published_at,
            "parent_author": None
        })
        
    return comments

def get_elements_coordinates_and_roles(driver):
    comments_elements_info = []
    try:
        js_script = """
        var results = [];
        var container = document.querySelector('div[role="main"]') || document.querySelector('div[role="dialog"]') || document;
        var allArticles = container.querySelectorAll('[role="article"]');
        
        var commentEls = Array.from(allArticles).filter(function(el) {
            var label = (el.getAttribute('aria-label') || '').toLowerCase();
            return label.includes('bình luận') || 
                   label.includes('phản hồi') || 
                   label.includes('comment') || 
                   label.includes('reply');
        });
        
        commentEls.forEach(function(commentEl) {
            // Find the author link that belongs directly to this comment
            var authorLink = Array.from(commentEl.querySelectorAll('a')).find(function(a) {
                var name = a.innerText.trim();
                return a.closest('[role="article"]') === commentEl && 
                       name.length >= 2 && 
                       !name.includes('\\n') && 
                       !['Thích', 'Like', 'Phản hồi', 'Reply', 'Chia sẻ', 'Share'].includes(name);
            });
            
            if (!authorLink) return;
            var authorName = authorLink.innerText.trim();
            
            // Find the text element that belongs directly to this comment and is not inside a link
            var textEl = Array.from(commentEl.querySelectorAll('[dir="auto"]')).find(function(el) {
                return el.closest('[role="article"]') === commentEl && 
                       !el.closest('a') && 
                       el.innerText.trim().length > 0;
            });
            
            var commentText = textEl ? textEl.innerText.trim() : '';
            if (!commentText) return;
            
            // Extract likes count
            var likes = 0;
            var likeEls = commentEl.querySelectorAll('*');
            for (var j = 0; j < likeEls.length; j++) {
                var label = likeEls[j].getAttribute('aria-label') || '';
                if (label.toLowerCase().includes('thích') || label.toLowerCase().includes('like') || label.toLowerCase().includes('reaction')) {
                    var numText = likeEls[j].innerText.trim();
                    if (/^\\d+$/.test(numText)) {
                        likes = parseInt(numText);
                        break;
                    }
                }
            }
            
            // Determine coordinate for nesting check
            var rect = commentEl.getBoundingClientRect();
            
            results.push({
                author: authorName,
                text: commentText,
                likes: likes,
                x: rect.left,
                y: rect.top + window.scrollY
            });
        });
        
        results.sort(function(a, b) { return a.y - b.y; });
        return results;
        """
        comments_elements_info = driver.execute_script(js_script)
    except Exception as e:
        logger.warning(f"⚠️ Lỗi khi chạy JS đo tọa độ comment: {e}")
    
    return comments_elements_info

def scrape_facebook_post(driver, url, max_comments):
    logger.info(f"🌐 Đang mở bài viết Facebook: {url}")
    driver.get(url)
    time.sleep(7)
    
    current = driver.current_url.lower()
    logger.info(f"📍 URL bài viết thực tế sau khi tải: {driver.current_url}")
    
    # Check if we were redirected to the home page or watch home page
    if current.endswith("facebook.com/") or current.endswith("facebook.com") or "facebook.com/home.php" in current or "facebook.com/?ref=logo" in current:
        try:
            screenshot_dir = os.path.join(os.getcwd(), 'public')
            os.makedirs(screenshot_dir, exist_ok=True)
            driver.save_screenshot(os.path.join(screenshot_dir, 'login_error.png'))
            with open(os.path.join(screenshot_dir, 'login_error.html'), 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass
        raise Exception("Không thể truy cập bài viết. Trình duyệt bị điều hướng về trang chủ Facebook. Hãy kiểm tra xem: 1) Liên kết bài viết có đúng không, 2) Bài viết có ở chế độ riêng tư/nhóm kín không, hoặc 3) Tài khoản cookie bạn dán vào có quyền xem bài viết này không.")
        
    expand_comments(driver, max_comments)
    
    logger.info("📊 Bắt đầu trích xuất nội dung bình luận...")
    raw_comments = get_elements_coordinates_and_roles(driver)
    
    if not raw_comments:
        logger.warning("⚠️ Không lấy được bình luận nào bằng JS tọa độ, thử dùng BeautifulSoup dự phòng...")
        html = driver.page_source
        comments = parse_comments(html, url)
    else:
        comments = []
        last_parent_author = None
        min_x = None
        
        for c in raw_comments:
            x = c['x']
            author = c['author']
            text = c['text']
            likes = c['likes']
            
            if min_x is None:
                min_x = x
            elif x < min_x:
                min_x = x
                
            if x > min_x + 15:
                comment_type = "reply"
                parent_author = last_parent_author
            else:
                comment_type = "comment"
                parent_author = None
                last_parent_author = author
                
            comments.append({
                "video_id": url,
                "type": comment_type,
                "author": author,
                "text": text,
                "likes": likes,
                "published_at": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                "parent_author": parent_author
            })
            
    try:
        screenshot_dir = os.path.join(os.getcwd(), 'public')
        os.makedirs(screenshot_dir, exist_ok=True)
        driver.save_screenshot(os.path.join(screenshot_dir, 'login_error.png'))
        with open(os.path.join(screenshot_dir, 'login_error.html'), 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info("📸 Đã lưu ảnh chụp màn hình trạng thái cuối cùng của trang tại public/login_error.png")
    except Exception as ex:
        logger.warning(f"⚠️ Không thể lưu ảnh chụp màn hình debug: {ex}")

    logger.info(f"✅ Thành công: Đã lấy được {len(comments)} bình luận từ {url}")
    return comments

def load_fb_cookie_string(driver, cookie_str):
    try:
        logger.info("🔑 Đang tiến hành đăng nhập Facebook bằng Cookie...")
        driver.get("https://www.facebook.com")
        time.sleep(4)
        
        # Check and handle cookie banner
        cookie_xpaths = [
            "//button[@data-cookiebanner='accept_button']",
            "//button[contains(@data-testid, 'cookie-policy')]",
            "//button[contains(text(), 'Allow')]",
            "//button[contains(text(), 'Accept')]",
            "//span[contains(text(), 'Cho phép')]/..",
            "//button[contains(text(), 'Cho phép')]",
            "//button[contains(text(), 'Chấp nhận')]"
        ]
        for xpath in cookie_xpaths:
            try:
                btn = driver.find_element(By.XPATH, xpath)
                driver.execute_script("arguments[0].click();", btn)
                logger.info("🍪 Đã đóng cookie banner trong lúc nạp cookie.")
                time.sleep(1)
                break
            except Exception:
                pass
                
        # Parse cookie string dynamically (supports Netscape with tabs or spaces, and standard key=val pairs)
        parsed_cookies = []
        lines = [l.strip() for l in cookie_str.split('\n') if l.strip()]
        
        # Count lines looking like Netscape format (7 columns)
        netscape_lines_count = 0
        for line in lines:
            if line.startswith("#"):
                continue
            parts = line.split('\t')
            if len(parts) < 7:
                parts = line.split()
            if len(parts) >= 7:
                netscape_lines_count += 1
                
        if netscape_lines_count > 0 or "# Netscape" in cookie_str or "\t" in cookie_str:
            logger.info("ℹ️ Đang phân tích Cookie định dạng Netscape...")
            for line in lines:
                if line.startswith("#"):
                    continue
                parts = line.split('\t')
                if len(parts) < 7:
                    parts = line.split()
                if len(parts) >= 7:
                    domain = parts[0]
                    path = parts[2]
                    name = parts[5]
                    val = parts[6]
                    parsed_cookies.append({
                        "name": name.strip(),
                        "value": val.strip(),
                        "domain": domain.strip(),
                        "path": path.strip()
                    })
        
        # If not parsed as Netscape, parse as standard key=val pairs
        if not parsed_cookies:
            logger.info("ℹ️ Đang phân tích Cookie định dạng chuỗi key=val...")
            pairs = []
            if ";" in cookie_str:
                pairs = cookie_str.split(";")
            else:
                pairs = lines
                
            for pair in pairs:
                pair = pair.strip()
                if not pair or "=" not in pair:
                    continue
                name, val = pair.split("=", 1)
                parsed_cookies.append({
                    "name": name.strip(),
                    "value": val.strip(),
                    "domain": ".facebook.com",
                    "path": "/"
                })
                
        # Add the parsed cookies to Selenium driver
        added_count = 0
        for c in parsed_cookies:
            try:
                driver.add_cookie(c)
                added_count += 1
            except Exception as cookie_err:
                pass
                
        logger.info(f"🍪 Đã nạp {added_count} cookie vào trình duyệt. Đang tải lại trang...")
        driver.get("https://www.facebook.com")
        time.sleep(6)
        
        # Verify authenticated state
        is_logged_in = False
        for xpath in [
            "//input[@placeholder='Tìm kiếm trên Facebook']",
            "//a[@aria-label='Facebook']",
            "//div[@role='navigation']",
            "//a[contains(@href, '/me/')]",
            "//div[contains(@aria-label, 'Xem thêm thông tin')]"
        ]:
            try:
                if driver.find_element(By.XPATH, xpath):
                    is_logged_in = True
                    break
            except Exception:
                continue
                
        if is_logged_in:
            logger.info("✅ Đăng nhập bằng Cookie thành công!")
        else:
            raise Exception("Đăng nhập bằng Cookie thất bại. Cookie có thể đã hết hạn hoặc thiếu trường xác thực (c_user, xs).")
            
    except Exception as e:
        logger.error(f"❌ Nạp Cookie thất bại: {e}")
        try:
            screenshot_dir = os.path.join(os.getcwd(), 'public')
            os.makedirs(screenshot_dir, exist_ok=True)
            driver.save_screenshot(os.path.join(screenshot_dir, 'login_error.png'))
            with open(os.path.join(screenshot_dir, 'login_error.html'), 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass
        raise e

def login_facebook_if_needed(driver, email, password, totp_secret=None):
    if not email or not password:
        return
    logger.info("🔑 Đang kiểm tra trạng thái đăng nhập Facebook...")
    driver.get("https://www.facebook.com/login.php")
    time.sleep(4)
    logger.info(f"📍 Trang đăng nhập hiện tại: {driver.current_url} | Tiêu đề: {driver.title}")
    
    # Check if already logged in
    is_logged_in = False
    for xpath in [
        "//input[@placeholder='Tìm kiếm trên Facebook']",
        "//a[@aria-label='Facebook']",
        "//div[@role='navigation']"
    ]:
        try:
            if driver.find_element(By.XPATH, xpath):
                is_logged_in = True
                break
        except Exception:
            continue
            
    if is_logged_in:
        logger.info("✅ Đã đăng nhập Facebook sẵn.")
        return
        
    logger.info("🔑 Chưa đăng nhập. Tiến hành xử lý Cookie banner và đăng nhập...")
    
    # Cookie consent banner acceptance
    cookie_xpaths = [
        "//button[@data-cookiebanner='accept_button']",
        "//button[contains(@data-testid, 'cookie-policy')]",
        "//button[contains(text(), 'Allow')]",
        "//button[contains(text(), 'Accept')]",
        "//span[contains(text(), 'Cho phép')]/..",
        "//button[contains(text(), 'Cho phép')]",
        "//button[contains(text(), 'Chấp nhận')]"
    ]
    for xpath in cookie_xpaths:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            driver.execute_script("arguments[0].click();", btn)
            logger.info("🍪 Đã chấp nhận cookie banner.")
            time.sleep(2)
            break
        except Exception:
            pass

    try:
        # Find email input
        email_input = None
        for selector in [
            (By.ID, "email"),
            (By.NAME, "email"),
            (By.XPATH, "//input[@type='text']"),
            (By.XPATH, "//input[@placeholder='Email' or @placeholder='Số điện thoại']")
        ]:
            try:
                el = driver.find_element(*selector)
                email_input = el
                break
            except Exception:
                continue

        # Find password input
        pass_input = None
        for selector in [
            (By.ID, "pass"),
            (By.NAME, "pass"),
            (By.XPATH, "//input[@type='password']"),
            (By.XPATH, "//input[@placeholder='Mật khẩu' or @placeholder='Password']")
        ]:
            try:
                el = driver.find_element(*selector)
                pass_input = el
                break
            except Exception:
                continue

        # Find login button
        login_btn = None
        for selector in [
            (By.NAME, "login"),
            (By.ID, "loginbutton"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//input[@type='submit']")
        ]:
            try:
                el = driver.find_element(*selector)
                login_btn = el
                break
            except Exception:
                continue

        if email_input and pass_input and login_btn:
            email_input.clear()
            email_input.send_keys(email)
            time.sleep(0.5)
            pass_input.clear()
            pass_input.send_keys(password)
            time.sleep(0.5)
            
            driver.execute_script("arguments[0].click();", login_btn)
            logger.info("⏳ Đã bấm nút đăng nhập. Chờ điều hướng...")
            time.sleep(8)
            
            logger.info(f"📍 URL sau khi gửi thông tin: {driver.current_url} | Tiêu đề: {driver.title}")
            
            # Check if Passkey prompt is requested
            is_passkey_page = "auth_platform/passkey" in driver.current_url.lower()
            if is_passkey_page:
                logger.info("🔑 Facebook hiển thị trang Passkey (xác thực thiết bị). Đang tìm cách chuyển sang OTP...")
                time.sleep(3)
                try:
                    # Look for "Try another way" or "Thử cách khác"
                    try_another_way_btn = None
                    for selector in [
                        (By.XPATH, "//*[contains(text(), 'Thử cách khác') or contains(text(), 'Try another way') or contains(text(), 'phương thức khác') or contains(text(), 'other way')]"),
                        (By.XPATH, "//div[@role='button'][contains(., 'Thử') or contains(., 'Try') or contains(., 'Other')]")
                    ]:
                        try:
                            elements = driver.find_elements(*selector)
                            for el in elements:
                                if el.is_displayed() and el.is_enabled():
                                    try_another_way_btn = el
                                    break
                            if try_another_way_btn:
                                break
                        except Exception:
                            continue
                            
                    if try_another_way_btn:
                        driver.execute_script("arguments[0].click();", try_another_way_btn)
                        logger.info("✅ Đã bấm nút 'Thử cách khác' trên trang Passkey.")
                        time.sleep(4)
                        
                        # Now select the "Use authenticator app" or "Use verification code" or "SMS" option
                        option_btn = None
                        for selector in [
                            (By.XPATH, "//*[contains(text(), 'ứng dụng xác thực') or contains(text(), 'authenticator') or contains(text(), 'mã xác thực') or contains(text(), 'verification code') or contains(text(), 'tin nhắn') or contains(text(), 'text message') or contains(text(), 'SMS')]"),
                            (By.XPATH, "//*[contains(text(), 'Gửi mã') or contains(text(), 'Send code')]")
                        ]:
                            try:
                                elements = driver.find_elements(*selector)
                                for el in elements:
                                    if el.is_displayed() and el.is_enabled():
                                        option_btn = el
                                        break
                                if option_btn:
                                    break
                            except Exception:
                                continue
                                
                        if option_btn:
                            driver.execute_script("arguments[0].click();", option_btn)
                            logger.info("✅ Đã chọn phương thức xác thực bằng mã OTP.")
                            time.sleep(5)
                        else:
                            logger.warning("⚠️ Không tìm thấy tùy chọn OTP trong danh sách phương thức khác.")
                    else:
                        logger.warning("⚠️ Không tìm thấy nút 'Thử cách khác' trên trang Passkey.")
                except Exception as passkey_err:
                    logger.error(f"❌ Lỗi khi xử lý trang Passkey: {passkey_err}")

            # Check if 2FA code is requested (check URL or page elements)
            is_2fa_page = False
            if "two_step_verification" in driver.current_url.lower() or "checkpoint" in driver.current_url.lower():
                is_2fa_page = True
            else:
                for xpath in [
                    "//input[@id='approvals_code']",
                    "//input[@name='approvals_code']",
                    "//*[contains(text(), 'mã xác thực') or contains(text(), '2-factor') or contains(text(), 'Two-factor') or contains(text(), 'xác thực 2 yếu tố')]"
                ]:
                    try:
                        if driver.find_elements(By.XPATH, xpath):
                            is_2fa_page = True
                            break
                    except Exception:
                        continue
                        
            if is_2fa_page:
                logger.info("🔐 Facebook yêu cầu mã xác thực 2 yếu tố (2FA)...")
                time.sleep(3)
                if totp_secret:
                    try:
                        import pyotp
                        totp = pyotp.TOTP(totp_secret.replace(" ", ""))
                        otp_code = totp.now()
                        logger.info(f"🔑 Đã tự động tạo mã OTP 2FA: {otp_code}")
                        
                        code_input = None
                        for selector in [
                            (By.ID, "approvals_code"),
                            (By.NAME, "approvals_code"),
                            (By.XPATH, "//input[@type='text' or @type='number']"),
                            (By.CSS_SELECTOR, "input[autocomplete='one-time-code']"),
                            (By.CSS_SELECTOR, "input")
                        ]:
                            try:
                                elements = driver.find_elements(*selector)
                                for el in elements:
                                    if el.is_displayed() and el.is_enabled():
                                        code_input = el
                                        break
                                if code_input:
                                    break
                            except Exception:
                                continue
                                
                        if code_input:
                            code_input.clear()
                            code_input.send_keys(otp_code)
                            logger.info("✅ Đã điền mã OTP 2FA.")
                            time.sleep(1.5)
                            
                            submit_btn = None
                            for selector in [
                                (By.ID, "checkpointSubmitButton"),
                                (By.XPATH, "//button[@id='checkpointSubmitButton']"),
                                (By.XPATH, "//button[@type='submit']"),
                                (By.XPATH, "//button[contains(., 'Tiếp tục') or contains(., 'Continue') or contains(., 'Gửi') or contains(., 'Submit') or contains(., 'Xác nhận')]"),
                                (By.XPATH, "//*[@role='button' and (contains(., 'Tiếp tục') or contains(., 'Continue'))]")
                            ]:
                                try:
                                    elements = driver.find_elements(*selector)
                                    for el in elements:
                                        if el.is_displayed() and el.is_enabled():
                                            submit_btn = el
                                            break
                                    if submit_btn:
                                        break
                                except Exception:
                                    continue
                                    
                            if submit_btn:
                                driver.execute_script("arguments[0].click();", submit_btn)
                                logger.info("⏳ Đã gửi mã 2FA. Chờ xác thực...")
                                time.sleep(10)
                                
                                # Check if it asks to save browser or if it asks "Trust this browser?"
                                for i in range(2):
                                    try:
                                        trust_btn = driver.find_element(By.XPATH, "//button[@id='checkpointSubmitButton'] or //button[contains(., 'Tiếp tục') or contains(., 'Continue') or contains(., 'Lưu trình duyệt') or contains(., 'Save Browser')]")
                                        if trust_btn.is_displayed():
                                            driver.execute_script("arguments[0].click();", trust_btn)
                                            logger.info("✅ Đã bấm Tiếp tục qua bước Lưu trình duyệt / Tin cậy thiết bị")
                                            time.sleep(6)
                                    except Exception:
                                        break
                            else:
                                logger.error("❌ Không tìm thấy nút Submit mã 2FA!")
                        else:
                            logger.error("❌ Không tìm thấy ô nhập mã 2FA!")
                    except Exception as pyotp_err:
                        logger.error(f"❌ Lỗi tự động tạo/nhập mã 2FA: {pyotp_err}")
                else:
                    logger.warning("⚠️ Tài khoản yêu cầu 2FA nhưng không tìm thấy cấu hình FB_2FA_SECRET!")
            
            # Save screenshot of the actual verification state before attempting to navigate away
            if "two_step_verification" in driver.current_url.lower() or "checkpoint" in driver.current_url.lower() or "auth_platform" in driver.current_url.lower():
                try:
                    screenshot_dir = os.path.join(os.getcwd(), 'public')
                    os.makedirs(screenshot_dir, exist_ok=True)
                    driver.save_screenshot(os.path.join(screenshot_dir, 'login_error.png'))
                    with open(os.path.join(screenshot_dir, 'login_error.html'), 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    logger.info("📸 Đã chụp ảnh màn hình trạng thái xác thực hiện tại (Passkey/2FA) tại public/login_error.png")
                except Exception:
                    pass

            # Go to home page to check login state
            driver.get("https://www.facebook.com/")
            time.sleep(5)
            
            is_logged_in_final = False
            for xpath in [
                "//input[@placeholder='Tìm kiếm trên Facebook']",
                "//a[@aria-label='Facebook']",
                "//div[@role='navigation']",
                "//a[contains(@href, '/me/')]",
                "//div[contains(@aria-label, 'Xem thêm thông tin')]"
            ]:
                try:
                    if driver.find_element(By.XPATH, xpath):
                        is_logged_in_final = True
                        break
                except Exception:
                    continue
            
            if is_logged_in_final:
                logger.info("✅ Đăng nhập thành công và xác thực trạng thái hoạt động.")
            else:
                if "two_step_verification" in driver.current_url or "checkpoint" in driver.current_url:
                    raise Exception(f"Tài khoản yêu cầu xác thực 2 lớp (2FA). Trình duyệt đang đứng tại: {driver.current_url}")
                else:
                    raise Exception(f"Không thể đăng nhập vào Facebook. Thông tin tài khoản/mật khẩu có thể không chính xác. Trình duyệt đang đứng tại: {driver.current_url}")
        else:
            raise Exception("Không tìm thấy đủ các ô nhập email/mật khẩu hoặc nút đăng nhập để thực hiện đăng nhập Facebook.")
    except Exception as e:
        logger.error(f"❌ Đăng nhập tự động thất bại: {e}")
        try:
            screenshot_dir = os.path.join(os.getcwd(), 'public')
            os.makedirs(screenshot_dir, exist_ok=True)
            driver.save_screenshot(os.path.join(screenshot_dir, 'login_error.png'))
            with open(os.path.join(screenshot_dir, 'login_error.html'), 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info("📸 Đã chụp ảnh màn hình lỗi tại public/login_error.png và lưu HTML tại public/login_error.html")
        except Exception as ex:
            logger.error(f"❌ Không thể chụp ảnh màn hình lỗi: {ex}")
        raise e

def main():
    if len(sys.argv) < 2:
        logger.error("❌ Thiếu đối số đường dẫn file cấu hình JSON.")
        sys.exit(1)
        
    config_path = sys.argv[1]
    if not os.path.exists(config_path):
        logger.error(f"❌ File cấu hình không tồn tại: {config_path}")
        sys.exit(1)
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    urls = config.get("urls", [])
    user_data_dir = config.get("chrome_user_data", "")
    profile_name = config.get("chrome_profile", "Default")
    max_comments = config.get("max_comments", 1000)
    output_file = config.get("output_file", "")
    fb_email = config.get("fb_email", "")
    fb_password = config.get("fb_password", "")
    fb_cookie = config.get("fb_cookie", "")
    fb_2fa_secret = config.get("fb_2fa_secret", "") or os.environ.get("FB_2FA_SECRET", "")
    
    if not urls:
        logger.error("❌ Không có URL nào để cào.")
        sys.exit(1)
        
    if not output_file:
        logger.error("❌ Không có đường dẫn file kết quả đầu ra.")
        sys.exit(1)
        
    driver = None
    all_comments = []
    
    try:
        driver = init_driver(user_data_dir, profile_name)
        
        cookie_success = False
        if fb_cookie:
            try:
                load_fb_cookie_string(driver, fb_cookie)
                cookie_success = True
            except Exception as cookie_err:
                logger.warning(f"⚠️ Đăng nhập bằng Cookie thất bại ({cookie_err}). Thử chuyển sang tài khoản/mật khẩu...")
                
        if not cookie_success and fb_email and fb_password:
            login_facebook_if_needed(driver, fb_email, fb_password, fb_2fa_secret)
            
        for url in urls:
            try:
                comments = scrape_facebook_post(driver, url, max_comments)
                all_comments.extend(comments)
            except Exception as e:
                logger.error(f"❌ Lỗi khi cào URL {url}: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logger.info("🔒 Đã đóng trình duyệt Chrome.")
            
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
        
    logger.info(f"🎉 Hoàn thành cào dữ liệu! Kết quả đã được lưu tại {output_file}")

if __name__ == "__main__":
    main()
