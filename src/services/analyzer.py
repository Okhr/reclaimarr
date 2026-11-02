from datetime import datetime, timedelta, timezone
from ..models.media import Media
from ..utils.logger import setup_logger
from ..config import STRATEGY

logger = setup_logger()


class MediaAnalyzer:
    """
    Analyzes and sorts media based on deletion priority rules.
    """

    def __init__(self, min_age_days: int):
        """
        Initializes the MediaAnalyzer.

        Args:
            min_age_days (int): The minimum age in days for a media item to be considered for deletion.
        """
        if min_age_days < 0:
            raise ValueError("Minimum age must be a non-negative number.")
        self.min_age_days = min_age_days
        logger.info(f"MediaAnalyzer initialized with a minimum media age of {min_age_days} days.")

    def analyze_and_sort(self, media_list: list[Media]) -> list[Media]:
        """
        Filters and sorts a list of media items for deletion.

        Args:
            media_list (list[Media]): The list of media items to analyze.

        Returns:
            list[Media]: A sorted list of media items prioritized for deletion.
        """
        logger.info("Starting media analysis and sorting...")

        # 1. Filter by age
        eligible_media = self._filter_by_age(media_list)

        # 2. Sort for deletion
        sorted_media = self._sort_for_deletion(eligible_media)

        logger.info(f"Analysis complete. {len(sorted_media)} media items are eligible for deletion.")
        return sorted_media

    def _filter_by_age(self, media_list: list[Media]) -> list[Media]:
        """
        Filters out media items that are newer than the specified minimum age.
        """
        if self.min_age_days == 0:
            logger.info("Minimum age is 0, all media items are eligible.")
            return media_list

        age_threshold = datetime.now(timezone.utc) - timedelta(days=self.min_age_days)
        logger.debug(f"Filtering with age threshold: {age_threshold}")

        filtered_list = []
        for media in media_list:
            if not media.added_date:
                logger.debug(f"Skipping '{media.title}' due to missing added_date.")
                continue

            is_eligible = media.added_date < age_threshold
            if is_eligible:
                filtered_list.append(media)

        logger.info(f"Filtered {len(media_list) - len(filtered_list)} items based on age.")
        return filtered_list

    def _sort_for_deletion(self, media_list: list[Media]) -> list[Media]:
        """
        Sorts media based on the selected deletion strategy.

        PRESERVE_WATCHED:
        1. Never-watched media (oldest added first).
        2. Watched media (oldest last watch date first).

        MERGE_LAST_WATCHED_DATE_ADDED:
        1. If media has a playback event, overwrite the media date_added with the most
           recent playback date.
        2. Sort on date_added (oldest first)
        """

        logger.info(f"Using {STRATEGY} strategy for sorting the deletion list")
        match STRATEGY:
            case "MERGE_LAST_WATCHED_DATE_ADDED":
                merged_media_list = media_list
                for item in merged_media_list:
                    # Update media date added with most recent playback date
                    if item.playbacks:
                        most_recent_playback = max(item.playbacks, key=lambda p: p.playback_date)
                        item.added_date = most_recent_playback.playback_date
                
                # Sort merged media list on date added (oldest first)
                merged_media_list.sort(key=lambda m: m.added_date)

                logger.info(f"Sorting complete. Found {len(merged_media_list)} item.")

                return merged_media_list

            case "PRESERVE_WATCHED":
                # Separate media into watched and never-watched lists
                never_watched = [m for m in media_list if not m.playbacks]
                watched = [m for m in media_list if m.playbacks]

                # Sort never-watched media by added date (oldest first)
                never_watched.sort(key=lambda m: m.added_date)

                # Sort watched media by last watch date (oldest first)
                watched.sort(key=lambda m: m.last_watch_date)

                logger.info(f"Sorting complete. Found {len(never_watched)} never-watched items and {len(watched)} watched items.")

                # Combine the lists, with never-watched items having higher priority
                return never_watched + watched
            case _:
                raise ValueError("Invalid sort strategy detected.")


if __name__ == '__main__':
    from ..models.media import Movie, TVShow
    from ..models.playback import Playback

    logger.info("--- Testing MediaAnalyzer ---")

    # Create sample media data
    media_items = [
        # Recently added, should be filtered out
        Movie("mov1", "New Movie", datetime.now() - timedelta(days=10), 1, playbacks=[]),
        # Old, never watched
        Movie("mov2", "Old Unwatched Movie", datetime(2022, 1, 1), 1, playbacks=[]),
        # Very old, never watched
        Movie("mov3", "Very Old Unwatched Movie", datetime(2021, 1, 1), 1, playbacks=[]),
        # Watched recently
        TVShow("show1", "Popular Show", datetime(2022, 5, 1), 1, playbacks=[Playback(datetime.now() - timedelta(days=30), 20, "u1", "a", "s1e1")]),
        # Watched long ago
        TVShow("show2", "Old Show", datetime(2021, 6, 1), 1, playbacks=[Playback(datetime(2022, 2, 1), 20, "u1", "a", "s2e1")]),
    ]

    # Initialize analyzer with a 90-day minimum age
    analyzer = MediaAnalyzer(min_age_days=90)

    # Run the analysis
    sorted_for_deletion = analyzer.analyze_and_sort(media_items)

    print("\n--- Deletion Priority Order ---")
    for i, media in enumerate(sorted_for_deletion):
        last_watched_str = f"Last Watched: {media.last_watch_date.date()}" if media.last_watch_date else "Never Watched"
        print(f"{i+1}. {media.title} (Added: {media.added_date.date()}, {last_watched_str})")
    print("-------------------------------")

    # Expected order:
    # 1. Very Old Unwatched Movie (oldest added, never watched)
    # 2. Old Unwatched Movie (next oldest added, never watched)
    # 3. Old Show (watched, but longest ago)
    # (New Movie and Popular Show are excluded due to age or recent watch date)
