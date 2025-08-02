from bs4 import BeautifulSoup
import requests
from pathlib import Path
import os
import sys
from tqdm import tqdm
import time
from loguru import logger


class AnimeDownloader:
    def __init__(self):
        # Logging setup
        logger.remove()
        logger.add(sys.stderr, level="ERROR")
        logger.add("anime_downloader.log", rotation="10 MB", level="ERROR")

        self.headers = {
            # To bypass Cloudflare protection, replace the User-Agent with your own.
            # You can find it in your browser's developer tools (F12 -> Network -> any request -> Headers).
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0"
        }
        self.session = requests.Session()
        self.load_cookies()
        self.proxies = []
        self.timeout = 10
        self.current_proxy = None
        self.load_proxies()

    def load_cookies(self):
        """Load cookies from cookies.txt file (Netscape format)"""
        cookie_file = Path("cookies.txt")
        if not cookie_file.exists():
            logger.info("cookies.txt file not found. Requests will be made without cookies.")
            return

        logger.info("Loading cookies from cookies.txt...")
        try:
            with open(cookie_file, "r") as f:
                for line in f:
                    if line.startswith("#") or line.strip() == "":
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) == 7:
                        domain, _, path, secure, _, name, value = parts
                        self.session.cookies.set(
                            name=name,
                            value=value,
                            domain=domain,
                            path=path,
                            secure=secure.lower() == 'true'
                        )
            logger.info("Cookies loaded into session successfully.")
        except Exception as e:
            logger.error(f"Error loading cookies from file: {e}")

    def load_proxies(self):
        """Load proxies from proxies.txt file"""
        proxy_file = Path("proxies.txt")
        if proxy_file.exists():
            with open(proxy_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if not line.startswith("socks5://"):
                            line = f"socks5://{line}"
                        self.proxies.append(line)
            if self.proxies:
                logger.info(f"Loaded {len(self.proxies)} proxies")
                self.apply_proxy()
            else:
                logger.info("No proxies found in the file. Continuing without proxies.")
        else:
            logger.info("proxies.txt file not found. Continuing without proxies.")

    def apply_proxy(self):
        """Apply a proxy from the list"""
        if not self.proxies:
            logger.info("No proxies found. Continuing without proxies.")
            self.session.proxies.clear()
            self.current_proxy = None
            return False

        try:
            self.current_proxy = self.proxies
            self.session.proxies.update(
                {"http": self.current_proxy, "https": self.current_proxy}
            )
            logger.info(f"Using proxy: {self.current_proxy}")

            # Proxy check
            test_url = "https://jut.su"
            try:
                test_response = self.session.get(test_url, timeout=self.timeout)
                logger.info(f"Proxy is working, status: {test_response.status_code}")
                return True
            except Exception as e:
                logger.error(f"Proxy is not working: {str(e)}")
                self.proxies.remove(self.current_proxy)
                if self.proxies:
                    logger.info("Trying another proxy...")
                    return self.apply_proxy()
                else:
                    logger.info("No working proxies found. Continuing without proxies.")
                    self.session.proxies.clear()
                    self.current_proxy = None
                    return False
        except Exception as e:
            logger.error(f"Error setting proxy: {str(e)}")
            self.session.proxies.clear()
            self.current_proxy = None
            return False

    def safe_request(self, url, stream=False):
        """Safe request with error handling and retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if stream:
                    return self.session.get(
                        url, headers=self.headers, stream=True, timeout=self.timeout
                    )
                else:
                    return self.session.get(
                        url, headers=self.headers, timeout=self.timeout
                    )
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error ({attempt + 1}/{max_retries}): {str(e)}")
                if "Tunnel connection failed" in str(
                    e
                ) or "SOCKSHTTPConnectionPool" in str(e):
                    logger.info("Problem with proxy, trying another one...")
                    if not self.apply_proxy() and attempt == max_retries - 1:
                        logger.info("Trying without proxy...")
                        self.session.proxies.clear()
                        self.current_proxy = None
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)

    def extract_episode_info(self, url_path):
        """Extract episode information from URL"""
        parts = url_path.strip("/").split("/")
        anime_name = parts[0]
        result = None

        if len(parts) == 1:
            result = {
                "anime_name": anime_name,
                "season": "season-1",
                "season_num": 1,
                "episode_type": "episode",
                "episode_num": 1,
            }
        elif len(parts) == 3:
            season_num = int(parts[1][7:])
            episode_num = int(parts[2][8:].split(".")[0])
            result = {
                "anime_name": anime_name,
                "season": parts[1],
                "season_num": season_num,
                "episode_type": "episode",
                "episode_num": episode_num,
            }
        elif len(parts) == 2:
            if parts[1].startswith("episode-"):
                episode_num = int(parts[1][8:].split(".")[0])
                result = {
                    "anime_name": anime_name,
                    "season": "season-1",
                    "season_num": 1,
                    "episode_type": "episode",
                    "episode_num": episode_num,
                }
            else:
                film_num = int(parts[1][5:].split(".")[0])
                result = {
                    "anime_name": anime_name,
                    "season": "films",
                    "season_num": 0,
                    "episode_type": "film",
                    "episode_num": film_num,
                }

        if not result:
            logger.error(f"Unknown URL format: {url_path}")
            return None
        return result

    def download_episode(self, url, output_path, quality, episode_num, total_episodes):
        """Download a single episode with a progress bar"""
        os.makedirs(Path("/".join(output_path.rsplit("/")[:-1])), exist_ok=True)

        if output_path.split("/")[-1] in os.listdir(
            Path("/".join(output_path.rsplit("/")[:-1]))
        ):
            logger.info(f"Episode already downloaded: {output_path}")
            return True

        try:
            logger.info(
                f"Getting information about episode {episode_num}/{total_episodes}..."
            )
            response = self.safe_request(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Attempt to find video in the specified quality
            all_qualities = ["1080", "720", "480", "360"]
            current_quality = quality
            video_source = None

            logger.info(f"Searching for video in {current_quality}p quality...")
            while not video_source:
                video_source = soup.find("source", {"res": current_quality})

                if not video_source:
                    try:
                        # Trying the next lower quality
                        quality_index = all_qualities.index(current_quality)
                        if quality_index < len(all_qualities) - 1:
                            current_quality = all_qualities[quality_index + 1]
                            logger.info(
                                f"Quality {quality} is not available, trying {current_quality}"
                            )
                        else:
                            logger.error("No available video qualities found")
                            return False
                    except ValueError:
                        logger.error(f"Invalid quality: {current_quality}")
                        return False

            # Downloading video with a progress bar
            video_url = video_source["src"]
            print(
                f"Downloading [{episode_num}/{total_episodes}]: {output_path} ({current_quality}p)"
            )

            response = self.safe_request(video_url, stream=True)
            total_size = int(response.headers.get("content-length", 0))

            with open(output_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"Episode {episode_num}/{total_episodes}",
                    bar_format="{l_bar}{bar:30}{r_bar}",
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            return True
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            if "Tunnel connection failed" in str(e) or "SOCKSHTTPConnectionPool" in str(
                e
            ):
                logger.info("Problem with proxy, trying another one...")
                if self.apply_proxy():
                    logger.info("Trying again with a new proxy...")
                    return self.download_episode(
                        url, output_path, quality, episode_num, total_episodes
                    )
            return False

    def get_episodes_list(self, url):
        """Get the list of all anime episodes"""
        logger.info(f"Getting episode list from {url}...")
        try:
            response = self.safe_request(url)
            soup = BeautifulSoup(response.text, "lxml")
            episodes = soup.find_all("a", {"class": "video"})

            if not episodes:
                logger.error("No episodes found or page is unavailable")
                if self.current_proxy and self.apply_proxy():
                    logger.info("Trying with another proxy...")
                    return self.get_episodes_list(url)
                return []

            logger.info(f"Found {len(episodes)} episodes")
            return episodes
        except Exception as e:
            logger.error(f"Error getting episode list: {str(e)}")
            if "Tunnel connection failed" in str(e) or "SOCKSHTTPConnectionPool" in str(
                e
            ):
                logger.info("Problem with proxy, trying another one...")
                if self.apply_proxy():
                    logger.info("Trying again with a new proxy...")
                    return self.get_episodes_list(url)
            return []

    def get_available_qualities(self, episode_url):
        """Get available video qualities"""
        logger.info(f"Getting available qualities for {episode_url}...")
        try:
            response = self.safe_request(episode_url)
            soup = BeautifulSoup(response.text, "lxml")
            sources = soup.find_all("source")

            if not sources:
                logger.error("No video sources found or page is unavailable")
                if self.current_proxy and self.apply_proxy():
                    logger.info("Trying with another proxy...")
                    return self.get_available_qualities(episode_url)
                return []

            qualities = [source.get("res") for source in sources if source.get("res")]
            logger.info(f"Available qualities: {', '.join(qualities)}")
            return qualities
        except Exception as e:
            logger.error(f"Error getting video qualities: {str(e)}")
            if "Tunnel connection failed" in str(e) or "SOCKSHTTPConnectionPool" in str(
                e
            ):
                logger.info("Problem with proxy, trying another one...")
                if self.apply_proxy():
                    logger.info("Trying again with a new proxy...")
                    return self.get_available_qualities(episode_url)
            return []

    def download_anime(
        self, url, quality, start_season=1, start_episode=1, include_films=False
    ):
        """Download all anime episodes from a specified season and episode"""
        logger.info("Getting episode list...")
        episodes = self.get_episodes_list(url)
        if not episodes:
            logger.error("Failed to get episode list")
            return

        logger.info("Organizing episodes by season...")
        # Organize episodes by season and number
        organized_episodes = {}

        for episode in episodes:
            href = episode["href"]

            # Extract information from the URL
            episode_info = self.extract_episode_info(href.strip("/"))
            if not episode_info:
                continue

            anime_name = episode_info["anime_name"]
            season = episode_info["season"]
            season_num = episode_info["season_num"]
            episode_type = episode_info["episode_type"]
            episode_num = episode_info["episode_num"]

            if season not in organized_episodes:
                organized_episodes[season] = {}

            organized_episodes[season][episode_num] = {
                "url": f"https://jut.su{href}",
                "name": anime_name,
                "season": season,
                "episode": f"{episode_type}-{episode_num}.mp4",
                "season_num": season_num,
                "episode_num": episode_num,
                "episode_type": episode_type,
            }

            logger.info(
                f"Added: {anime_name}, {season}, {episode_type} {episode_num}"
            )

        # Count the total number of episodes to download
        total_episodes = 0

        for season in organized_episodes:
            if not organized_episodes[season]:
                continue

            for episode_num in organized_episodes[season]:
                episode_data = organized_episodes[season][episode_num]
                season_num = episode_data["season_num"]
                episode_type = episode_data["episode_type"]

                # Check if this episode needs to be downloaded
                if episode_type == "film" and not include_films:
                    # Skip movies if the user did not request them
                    continue

                if season_num >= start_season or (
                    episode_type == "film" and include_films
                ):
                    if (
                        season_num > start_season
                        or episode_num >= start_episode
                        or episode_type == "film"
                    ):
                        total_episodes += 1

        print(f"Total episodes found for download: {total_episodes}")

        # Download episodes starting from the specified season and episode
        if total_episodes == 0:
            logger.error("No episodes to download from the specified season and episode")
            return

        current_episode = 1

        # Sort seasons by number
        sorted_seasons = sorted(
            organized_episodes.keys(),
            key=lambda s: organized_episodes[s][next(iter(organized_episodes[s]))][
                "season_num"
            ]
            if organized_episodes[s]
            else 0,
        )

        for season in sorted_seasons:
            if not organized_episodes[season]:
                continue

            # Sort episodes by number
            for episode_num in sorted(organized_episodes[season].keys()):
                episode_data = organized_episodes[season][episode_num]
                season_num = episode_data["season_num"]
                episode_type = episode_data["episode_type"]

                # Skip movies if the user did not request them
                if episode_type == "film" and not include_films:
                    continue

                # Skip seasons earlier than the starting one (but not movies, if they need to be downloaded)
                if season_num < start_season and not (
                    episode_type == "film" and include_films
                ):
                    continue

                # Skip episodes earlier than the starting one in the starting season (but not movies)
                if (
                    season_num == start_season
                    and episode_num < start_episode
                    and episode_type != "film"
                ):
                    continue

                # Create directory structure depending on the type
                if episode_data["episode_type"] == "film":
                    output_path = (
                        f"{episode_data['name']}/films/{episode_data['episode']}"
                    )
                else:
                    output_path = f"{episode_data['name']}/{episode_data['season']}/{episode_data['episode']}"

                success = self.download_episode(
                    episode_data["url"],
                    output_path,
                    quality,
                    current_episode,
                    total_episodes,
                )

                if success:
                    logger.info(
                        f"Successfully downloaded episode {current_episode}/{total_episodes}"
                    )
                else:
                    logger.error(
                        f"Failed to download episode {current_episode}/{total_episodes}"
                    )

                current_episode += 1


def main():
    print("Starting Anime Downloader...")
    downloader = AnimeDownloader()

    # Get anime URL
    url = input("Enter anime URL or name: ")
    if not url.startswith("http"):
        url = f"https://jut.su/{url}"

    print(f"Getting information about {url}...")

    # Check available qualities
    episodes = downloader.get_episodes_list(url)
    if not episodes:
        print(
            "Failed to get episode list. The anime may be blocked or unavailable."
        )
        sys.exit(1)

    # Get available qualities from the last episode
    print("Getting quality information...")
    last_episode_url = f"https://jut.su{episodes[-1]['href']}"
    qualities = downloader.get_available_qualities(last_episode_url)

    if not qualities:
        print(
            "Could not determine available qualities. The anime may be blocked in your region."
        )
        sys.exit(1)

    print("Available qualities:", " ".join(qualities))

    # Quality selection
    while True:
        quality = input("Choose quality: ")
        if quality in qualities:
            break
        print("Please enter one of the available qualities.")

    try:
        start_season = int(
            input("Which season to start downloading from (default 1): ") or "1"
        )
        start_episode = int(
            input("Which episode to start downloading from (default 1): ") or "1"
        )

        # Added choice to download movies
        include_films = input("Download movies? (yes/no, default no): ").lower()
        include_films = include_films in ["yes", "y", "1"]

    except ValueError:
        print("Invalid values entered, season 1, episode 1 will be used")
        start_season = 1
        start_episode = 1
        include_films = False

    # Start download
    print(f"Starting download from season {start_season}, episode {start_episode}...")
    if include_films:
        print("Movies will be included in the download")
    else:
        print("Movies will not be downloaded")

    downloader.download_anime(url, quality, start_season, start_episode, include_films)
    print("Download finished!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDownload stopped by user")
    except Exception as e:
        print(f"Critical error: {str(e)}")
        import traceback

        traceback.print_exc()