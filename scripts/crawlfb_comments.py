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
    
    dir_auto_tags = soup.find_all(lambda tag: tag.name in ['div', 'span'] and tag.get('dir') == 'auto')
    seen_comments = set()
    
    for tag in dir_auto_tags:
        text = tag.get_text().strip()
        if not text or len(text) < 1:
            continue
            
        author_name = None
        author_url = None
        comment_wrapper = None
        
        curr = tag
        for _ in range(5):
            if not curr:
                break
            links = curr.find_all('a', href=True)
            for link in links:
                href = link['href']
                link_text = link.get_text().strip()
                is_profile = False
                if 'profile.php' in href or '/user/' in href:
                    is_profile = True
                elif href.startswith('/') and len(href) > 2:
                    system_paths = ['/posts/', '/photos/', '/videos/', '/groups/', '/permalink', '/sharer', '/messages', '/notifications', '/watch', '/marketplace', '/friends', '/bookmark', '/policies', '/help', '/settings', '/privacy', '/home.php', '/ajax/', '/ads/', '/hashtag/']
                    if not any(sp in href for sp in system_paths):
                        is_profile = True
                
                if is_profile and link_text and link_text not in ['Thích', 'Like', 'Phản hồi', 'Reply', 'Chia sẻ', 'Share']:
                    author_name = link_text
                    author_url = "https://www.facebook.com" + href if href.startswith('/') else href
                    comment_wrapper = curr
                    break
            if author_name:
                break
            curr = curr.parent

        if author_name and comment_wrapper:
            unique_key = f"{author_name}|{text[:100]}"
            if unique_key in seen_comments:
                continue
            seen_comments.add(unique_key)

            likes = 0
            reaction_els = comment_wrapper.find_all(lambda tag: tag.name in ['div', 'span'] and tag.get('aria-label') and any(x in tag.get('aria-label').lower() for x in ['thích', 'like', 'reaction', 'bày tỏ']))
            for rx in reaction_els:
                rx_text = rx.get_text().strip()
                if rx_text.isdigit():
                    likes = int(rx_text)
                    break
            
            published_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            time_links = comment_wrapper.find_all('a', href=True)
            for link in time_links:
                href = link['href']
                if 'comment_id=' in href or '/posts/' in href or '/permalink' in href:
                    time_text = link.get_text().strip()
                    if time_text and len(time_text) < 15 and any(char.isdigit() for char in time_text):
                        published_at = time_text
                        break

            comments.append({
                "video_id": post_url,
                "type": "comment",
                "author": author_name,
                "text": text,
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
        var aTags = document.querySelectorAll('a[href*="profile.php"], a[href*="/user/"], a');
        var seenWrappers = new Set();
        
        aTags.forEach(function(a) {
            var href = a.getAttribute('href') || '';
            var name = a.innerText.trim();
            if (!name || name.length < 2 || name.includes('\\n') || ['Thích', 'Like', 'Phản hồi', 'Reply', 'Chia sẻ', 'Share'].includes(name)) return;
            
            var isProfile = false;
            if (href.includes('profile.php') || href.includes('/user/')) {
                isProfile = true;
            } else if (href.startsWith('/') && href.length > 2) {
                var systemPaths = ['/posts/', '/photos/', '/videos/', '/groups/', '/permalink', '/sharer', '/messages', '/notifications', '/watch', '/marketplace', '/friends', '/bookmark', '/policies', '/help', '/settings', '/privacy', '/home.php', '/ajax/', '/ads/', '/hashtag/'];
                var matchSystem = false;
                for (var i = 0; i < systemPaths.length; i++) {
                    if (href.includes(systemPaths[i])) { matchSystem = true; break; }
                }
                if (!matchSystem) isProfile = true;
            }
            
            if (!isProfile) return;
            
            var p = a.parentElement;
            var textEl = null;
            var wrapper = null;
            
            for (var i = 0; i < 5; i++) {
                if (!p) break;
                var dirAuto = p.querySelector('[dir="auto"]');
                if (dirAuto && dirAuto.innerText.trim().length > 0 && dirAuto !== a) {
                    textEl = dirAuto;
                    wrapper = p;
                    break;
                }
                p = p.parentElement;
            }
            
            if (wrapper && textEl && !seenWrappers.has(wrapper)) {
                seenWrappers.add(wrapper);
                var rect = wrapper.getBoundingClientRect();
                
                var likes = 0;
                var likeEls = wrapper.querySelectorAll('*');
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
                
                results.push({
                    author: name,
                    text: textEl.innerText.trim(),
                    likes: likes,
                    x: rect.left,
                    y: rect.top + window.scrollY
                });
            }
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
    time.sleep(5)
    
    for label in ["Đóng", "Close", "Not Now", "Lúc khác"]:
        try:
            driver.find_element(By.XPATH, f"//div[@aria-label='{label}']").click()
            logger.info(f"✅ Đã đóng popup '{label}'")
            time.sleep(1)
            break
        except NoSuchElementException:
            pass
            
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
            
    logger.info(f"✅ Thành công: Đã lấy được {len(comments)} bình luận từ {url}")
    return comments

def login_facebook_if_needed(driver, email, password):
    if not email or not password:
        return
    logger.info("🔑 Đang kiểm tra trạng thái đăng nhập Facebook...")
    driver.get("https://www.facebook.com/")
    time.sleep(3)
    
    # Check if already logged in (look for search bar or navigation)
    is_logged_in = False
    for xpath in [
        "//input[@placeholder='Tìm kiếm trên Facebook']",
        "//a[@aria-label='Facebook']",
        "//div[@role='navigation']"
    ]:
        try:
            if driver.find_element(By.XPATH, xpath).is_displayed():
                is_logged_in = True
                break
        except Exception:
            continue
            
    if is_logged_in:
        logger.info("✅ Đã đăng nhập Facebook sẵn.")
        return
        
    logger.info("🔑 Chưa đăng nhập. Đang tiến hành đăng nhập tự động...")
    try:
        email_input = driver.find_element(By.ID, "email")
        pass_input = driver.find_element(By.ID, "pass")
        login_btn = driver.find_element(By.NAME, "login")
        
        email_input.clear()
        email_input.send_keys(email)
        time.sleep(0.5)
        pass_input.clear()
        pass_input.send_keys(password)
        time.sleep(0.5)
        
        login_btn.click()
        logger.info("⏳ Chờ điều hướng đăng nhập...")
        time.sleep(6)
        
        # Verify login succeeded
        driver.get("https://www.facebook.com/")
        time.sleep(3)
        logger.info("✅ Hoàn tất đăng nhập.")
    except Exception as e:
        logger.error(f"❌ Đăng nhập tự động thất bại: {e}")

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
        
        # Log in if credentials provided
        if fb_email and fb_password:
            login_facebook_if_needed(driver, fb_email, fb_password)
            
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
