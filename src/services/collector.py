from ..config import JELLYSTAT_URL
from ..api.jellyfin import JellyfinClient
from ..api.jellystat import JellystatClient
from ..api.jellyseerr import JellyseerrClient
from ..api.radarr import RadarrClient
from ..api.sonarr import SonarrClient
from ..models.media import Media, Movie, TVShow
from ..models.playback import Playback
from ..utils.logger import setup_logger
from ..utils.date import parse_date

logger = setup_logger()


class DataCollector:
    """
    Collects and merges data from all configured APIs.
    """

    def __init__(self):
        """Initializes the DataCollector and all API clients."""
        logger.info("Initializing API clients...")
        self.jellyfin = JellyfinClient()
        if JELLYSTAT_URL:
            self.jellystat = JellystatClient()
        self.jellyseerr = JellyseerrClient()
        self.radarr = RadarrClient()
        self.sonarr = SonarrClient()
        logger.info("All API clients initialized.")

    def collect_all_media(self) -> list[Media]:
        """
        Orchestrates the collection and merging of all media data.

        Returns:
            list[Media]: A list of populated Movie and TVShow objects.
        """
        logger.info("Starting data collection process...")

        # 1. Fetch raw data from all APIs
        jellyfin_movies = self.jellyfin.get_all_movies()
        jellyfin_shows = self.jellyfin.get_all_shows()
        radarr_movies = self.radarr.get_all_movies()
        sonarr_series = self.sonarr.get_all_series()
        jellyseerr_requests = self.jellyseerr.get_all_requests()
        if JELLYSTAT_URL:
            playback_history = self.jellystat.get_playback_history()
        else:
            playback_history = self.jellyfin.get_playback_history()

        # 2. Create lookup maps for efficient merging
        radarr_map_imdb = {movie['imdbId']: movie for movie in radarr_movies if 'imdbId' in movie and movie['imdbId']}
        radarr_map_title = {movie['title']: movie for movie in radarr_movies}

        sonarr_map_imdb = {series['imdbId']: series for series in sonarr_series if 'imdbId' in series and series['imdbId']}
        sonarr_map_title = {series['title']: series for series in sonarr_series}

        request_map = {req['media']['jellyfinMediaId']: req for req in jellyseerr_requests if req.get('media') and req['media'].get('jellyfinMediaId')}

        # 3. Process and merge media items
        movies = self._merge_movie_data(jellyfin_movies, radarr_map_imdb, radarr_map_title, request_map)
        tv_shows, episode_to_show_map = self._merge_tv_show_data(jellyfin_shows, sonarr_map_imdb, sonarr_map_title, request_map)

        all_media = movies + tv_shows

        # 4. Attach playback data
        self._attach_playback_data(all_media, playback_history, episode_to_show_map)

        # 5. Final calculations
        for media in all_media:
            media.calculate_watch_ratio()
            media.calculate_last_watch_date()

        logger.info(f"Data collection complete. Total media items processed: {len(all_media)}")
        return all_media

    def _merge_movie_data(self, jf_movies: list[dict], radarr_map_imdb: dict, radarr_map_title: dict, request_map: dict) -> list[Movie]:
        """Merges Jellyfin, Radarr, and Jellyseerr data for movies."""
        merged_movies = []
        for jf_movie in jf_movies:
            title = jf_movie.get('Name')
            provider_ids = jf_movie.get('ProviderIds', {})
            imdb_id = provider_ids.get('Imdb')

            radarr_data = None
            if imdb_id and imdb_id in radarr_map_imdb:
                radarr_data = radarr_map_imdb[imdb_id]
            else:
                radarr_data = radarr_map_title.get(title)

            # Basic info from Jellyfin
            movie = Movie(
                jellyfin_id=jf_movie['Id'],
                title=title,
                added_date=None,  # Will be populated from Radarr
                file_size=jf_movie.get('MediaSources', [{}])[0].get('Size', 0),
                duration=jf_movie.get('RunTimeTicks', 0) / 600000000,  # Ticks to minutes
            )

            # Add Radarr info
            if radarr_data:
                movie.radarr_id = radarr_data.get('id')
                if not movie.file_size:  # Use Radarr file size if Jellyfin's is missing
                    movie.file_size = radarr_data.get('movieFile', {}).get('size', 0)
                # Prioritize Radarr's added date
                radarr_added_date = radarr_data.get('movieFile', {}).get('dateAdded')
                if radarr_added_date:
                    movie.added_date = parse_date(radarr_added_date)

            # Add Jellyseerr info
            request_data = request_map.get(movie.jellyfin_id)
            if request_data:
                movie.request_id = request_data.get('id')
                movie.requester_id = request_data.get('requestedBy', {}).get('id')
                movie.requester_name = request_data.get('requestedBy', {}).get('jellyfinUsername')

            merged_movies.append(movie)
        logger.info(f"Merged {len(merged_movies)} movies.")
        return merged_movies

    def _merge_tv_show_data(self, jf_shows: list[dict], sonarr_map_imdb: dict, sonarr_map_title: dict, request_map: dict) -> tuple[list[TVShow], dict[str, str]]:
        """Merges Jellyfin, Sonarr, and Jellyseerr data for TV shows."""
        merged_shows = []
        episode_to_show_map = {}
        for jf_show in jf_shows:
            title = jf_show.get('Name')
            provider_ids = jf_show.get('ProviderIds', {})
            imdb_id = provider_ids.get('Imdb')

            sonarr_data = None
            if imdb_id and imdb_id in sonarr_map_imdb:
                sonarr_data = sonarr_map_imdb[imdb_id]
            else:
                sonarr_data = sonarr_map_title.get(title)

            # Get episode details to calculate total duration and count
            episodes = self.jellyfin.get_episodes_for_show(jf_show['Id'])
            total_duration = sum(ep.get('RunTimeTicks', 0) / 600000000 for ep in episodes)

            show = TVShow(
                jellyfin_id=jf_show['Id'],
                title=title,
                added_date=None,  # Will be populated from Sonarr
                file_size=0,  # Will be summed from Sonarr data if available
                total_duration=total_duration,
                total_episodes=len(episodes)
            )

            # Add Sonarr info
            if sonarr_data:
                show.sonarr_id = sonarr_data.get('id')
                show.file_size = sonarr_data.get('statistics', {}).get('sizeOnDisk', 0)
                # Prioritize Sonarr's added date
                sonarr_added_date = sonarr_data.get('added')
                if sonarr_added_date:
                    show.added_date = parse_date(sonarr_added_date)

            # Add Jellyseerr info
            request_data = request_map.get(show.jellyfin_id)
            if request_data:
                show.request_id = request_data.get('id')
                show.requester_id = request_data.get('requestedBy', {}).get('id')
                show.requester_name = request_data.get('requestedBy', {}).get('jellyfinUsername')

            for episode in episodes:
                episode_to_show_map[episode['Id']] = show.jellyfin_id

            merged_shows.append(show)
        logger.info(f"Merged {len(merged_shows)} TV shows.")
        return merged_shows, episode_to_show_map

    def _attach_playback_data(self, media_list: list[Media], playback_history: list[dict], episode_to_show_map: dict[str, str]):
        """Attaches playback history to the corresponding media items."""
        media_map = {media.jellyfin_id: media for media in media_list}

        for record in playback_history:
            item_id = record.get('ItemId') or record.get('NowPlayingItemId')
            if not item_id:
                logger.warning(f"Skipping playback record with missing ItemId and NowPlayingItemId: {record}")
                continue

            media_item = media_map.get(item_id)

            # If not found, it might be an episode. Find the parent show.
            if not media_item:
                show_id = episode_to_show_map.get(item_id)
                if show_id:
                    media_item = media_map.get(show_id)

            if media_item:
                playback_date = parse_date(record.get('ActivityDateInserted'))
                if not playback_date:
                    logger.warning(f"Skipping playback record due to missing ActivityDateInserted: {record}")
                    continue

                playback = Playback(
                    playback_date=playback_date,
                    duration=record.get('PlaybackDuration', 0) / 60,  # Seconds to minutes
                    user_id=record.get('UserId'),
                    user_name=record.get('UserName'),
                    item_id=item_id
                )
                media_item.playbacks.append(playback)

        logger.info("Attached playback data to media items.")


if __name__ == '__main__':
    logger.info("--- Testing DataCollector ---")
    try:
        collector = DataCollector()
        all_media = collector.collect_all_media()

        if all_media:
            logger.info(f"Successfully collected {len(all_media)} media items.")

            movies = [m for m in all_media if isinstance(m, Movie)]
            shows = [m for m in all_media if isinstance(m, TVShow)]

            logger.info(f"Movies found: {len(movies)}")
            logger.info(f"TV Shows found: {len(shows)}")

            # Log details of the first movie with playback
            first_movie_with_playback = next((m for m in movies if m.playbacks), None)
            if first_movie_with_playback:
                logger.info("--- Example Movie ---")
                logger.info(f"Title: {first_movie_with_playback.title}")
                logger.info(f"Watch Ratio: {first_movie_with_playback.watch_ratio:.2%}")
                logger.info(f"Last Watched: {first_movie_with_playback.last_watch_date}")
                logger.info(f"Playbacks: {len(first_movie_with_playback.playbacks)}")

    except Exception as e:
        logger.error(f"An error occurred during DataCollector test: {e}", exc_info=True)
