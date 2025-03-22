from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException
)
from selenium.webdriver.common.keys import Keys
from typing import List, Optional
import logging
import time
import os


class MangaReader:
    def __init__(self, headless: bool = False, download_path: Optional[str] = None):
        """
        Initialize MangaReader with optional headless mode and download path.

        Args:
            headless: Whether to run browser in headless mode
            download_path: Path to save downloaded images
        """
        self.logger = self._setup_logging()
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless')

        if download_path:
            self.download_path = os.path.abspath(download_path)
            os.makedirs(self.download_path, exist_ok=True)
            self.options.add_experimental_option(
                "prefs",
                {
                    "download.default_directory": self.download_path,
                    "download.prompt_for_download": False,
                }
            )

        self.driver = None
        self.wait = None
        self.current_manga = None
        self.base_url = "https://cmangax.com/"

    def _setup_logging(self) -> logging.Logger:
        """Configure logging with more detailed format."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger(__name__)

    def _safe_click(self, element, retry_count: int = 3, delay: float = 1.0) -> bool:
        """
        Enhanced safe click with multiple retry strategies.

        Args:
            element: WebElement to click
            retry_count: Number of retries
            delay: Delay between retries
        """
        for attempt in range(retry_count):
            try:
                # Try regular click
                element.click()
                return True
            except ElementClickInterceptedException:
                self.logger.warning(f"Click intercepted, attempt {attempt + 1} of {retry_count}")
                try:
                    # Try JavaScript click
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    # Try scrolling into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(delay)
            except StaleElementReferenceException:
                self.logger.warning("Element became stale, refreshing...")
                time.sleep(delay)
                continue
        return False

    def _handle_popups(self, timeout: int = 5) -> None:
        """
        Enhanced popup handler with timeout and multiple window types.

        Args:
            timeout: Maximum time to spend handling popups
        """
        start_time = time.time()
        main_window = self.driver.current_window_handle

        while time.time() - start_time < timeout:
            try:
                # Handle popup windows
                for handle in self.driver.window_handles:
                    if handle != main_window:
                        self.driver.switch_to.window(handle)
                        self.driver.close()

                # Handle modal dialogs
                try:
                    dialog_close = self.driver.find_element(By.CSS_SELECTOR, "div.modal-close, button.close-dialog")
                    if dialog_close.is_displayed():
                        self._safe_click(dialog_close)
                except NoSuchElementException:
                    pass

                self.driver.switch_to.window(main_window)
                break

            except Exception as e:
                self.logger.error(f"Error handling popups: {e}")
                time.sleep(1)

    def start_session(self) -> bool:
        """Initialize webdriver session with error handling."""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.maximize_window()

            # Set page load timeout
            self.driver.set_page_load_timeout(30)

            # Navigate to base URL
            self.driver.get(self.base_url)
            return True

        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            return False

    def search_manga(self, manga_title: str) -> bool:
        """
        Enhanced search functionality with retry mechanism.

        Args:
            manga_title: Title of manga to search for
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Handle initial popup if present
                self._handle_popups()

                # Open search with retry
                search_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search_open"))
                )
                if not self._safe_click(search_button):
                    continue

                # Enter search term
                search_box = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.search_div input[placeholder='Tìm kiếm']")
                    )
                )
                search_box.clear()
                search_box.send_keys(manga_title)
                time.sleep(1)  # Allow search suggestions to load
                search_box.send_keys(Keys.RETURN)

                self.current_manga = manga_title
                return True

            except Exception as e:
                self.logger.error(f"Search attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return False
                self.driver.refresh()
                time.sleep(2)

    def select_first_result(self) -> bool:
        """Select first manga result with enhanced error handling."""
        try:
            # Wait for search results and verify they exist
            results = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.search_info"))
            )

            if not results:
                self.logger.error("No search results found")
                return False

            # Click first result with retry mechanism
            return self._safe_click(results[0])

        except TimeoutException:
            self.logger.error("Search results not found")
            return False
        except Exception as e:
            self.logger.error(f"Error selecting result: {e}")
            return False

    def read_chapter(self, chapter_number: int) -> bool:
        """
        Enhanced chapter reading with ad handling and image loading verification.

        Args:
            chapter_number: Chapter number to read
        """
        try:
            # Find and click chapter link
            chapter_selector = f"a[href*='chapter-{chapter_number}-']"
            chapter_link = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, chapter_selector)))
            if not self._safe_click(chapter_link):
                return False

            # Handle ads and popups
            self._handle_popups()

            # Wait for images to load
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.chapter-content img"))
            )

            # Scroll through chapter
            self._smooth_scroll()

            return True

        except Exception as e:
            self.logger.error(f"Error reading chapter {chapter_number}: {e}")
            return False

    def _smooth_scroll(self, pause_time: float = 0.5) -> None:
        """
        Implement smooth scrolling through the chapter.

        Args:
            pause_time: Time to pause between scrolls
        """
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        current_height = 0
        step = 300  # Pixels to scroll each time

        while current_height < total_height:
            current_height += step
            self.driver.execute_script(f"window.scrollTo(0, {current_height});")
            time.sleep(pause_time)

    def download_chapter(self, chapter_number: int) -> bool:
        """
        Download chapter images if download_path is configured.

        Args:
            chapter_number: Chapter number to download
        """
        if not hasattr(self, 'download_path'):
            self.logger.error("Download path not configured")
            return False

        try:
            # Create chapter directory
            chapter_dir = os.path.join(
                self.download_path,
                f"{self.current_manga}_chapter_{chapter_number}"
            )
            os.makedirs(chapter_dir, exist_ok=True)

            # Find all images
            images = self.driver.find_elements(By.CSS_SELECTOR, "div.chapter-content img")

            # Download each image
            for idx, img in enumerate(images, 1):
                src = img.get_attribute('src')
                if src:
                    # Use JavaScript to trigger download
                    self.driver.execute_script(
                        """
                        let a = document.createElement('a');
                        a.href = arguments[0];
                        a.download = arguments[1];
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        """,
                        src,
                        f"page_{idx:03d}.jpg"
                    )
                    time.sleep(0.5)  # Prevent overwhelming the server

            return True

        except Exception as e:
            self.logger.error(f"Error downloading chapter {chapter_number}: {e}")
            return False

    def close(self) -> None:
        """Safely close browser session."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.wait = None


def read_manga_by_chapters(
        manga_title: str,
        chapters: List[int],
        headless: bool = False,
        download_path: Optional[str] = None
) -> bool:
    """
    Enhanced main function with download support and better error handling.

    Args:
        manga_title: Title of manga to read
        chapters: List of chapter numbers to read
        headless: Whether to run in headless mode
        download_path: Optional path to save downloaded chapters
    """
    reader = MangaReader(headless=headless, download_path=download_path)
    success = True

    try:
        if not reader.start_session():
            return False

        if not reader.search_manga(manga_title):
            return False

        if not reader.select_first_result():
            return False

        for chapter in chapters:
            print(f"Reading chapter {chapter}...")

            if not reader.read_chapter(chapter):
                print(f"Failed to read chapter {chapter}")
                success = False
                continue

            if download_path and not reader.download_chapter(chapter):
                print(f"Failed to download chapter {chapter}")
                success = False

            time.sleep(2)  # Pause between chapters

        return success

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return False

    finally:
        reader.close()


if __name__ == "__main__":
    # Example usage with download support
    manga_title = "Tiểu Thư Đoản Mệnh Được Quản Gia Lạnh Lùng Bảo Bọc"
    chapters_to_read = [1, 2, 3]
    download_path = "manga_downloads"  # Optional

    success = read_manga_by_chapters(
        manga_title,
        chapters_to_read,
        headless=False,
        download_path=download_path
    )

    if success:
        print("Successfully finished reading specified chapters")
    else:
        print("Failed to complete reading all chapters")