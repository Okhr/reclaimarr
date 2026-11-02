import shutil
from tabulate import tabulate
from ..api.radarr import RadarrClient
from ..api.sonarr import SonarrClient
from ..api.jellyseerr import JellyseerrClient
from ..models.media import Media, Movie, TVShow
from ..utils.logger import setup_logger
from ..config import JELLYSEERR_DELETE_REQUESTS

logger = setup_logger()


class MediaDeleter:
    """
    Handles the deletion of media based on a prioritized list.
    """

    def __init__(self):
        """Initializes the MediaDeleter with API clients."""
        self.radarr = RadarrClient()
        self.sonarr = SonarrClient()
        self.jellyseerr = JellyseerrClient()
        logger.info("MediaDeleter initialized.")

    def delete_until_target(self, sorted_media: list[Media], target_usage: int, media_path: str, dry_run: bool):
        """
        Deletes media from the sorted list until disk usage is below the target.

        Args:
            sorted_media (list[Media]): A list of media items sorted by deletion priority.
            target_usage (int): The target disk usage percentage.
            media_path (str): The path to the media library for disk monitoring.
            dry_run (bool): If True, only log what would be deleted.
        """
        if dry_run:
            logger.warning("--- DRY RUN MODE ENABLED ---")
            logger.warning("No files will be deleted. The following actions would be taken:")

        try:
            total_space, used_space, _ = shutil.disk_usage(media_path)
        except FileNotFoundError:
            logger.error(f"Media path not found: {media_path}. Aborting deletion process.")
            return
        except Exception as e:
            logger.error(f"Error getting disk usage for {media_path}: {e}. Aborting deletion process.")
            return

        if total_space == 0:
            logger.warning("Total disk space is 0. Cannot calculate usage. Aborting.")
            return

        current_usage_percent = (used_space / total_space) * 100
        logger.info(f"Initial disk usage: {current_usage_percent:.2f}%. Target: {target_usage}%.")

        if current_usage_percent <= target_usage:
            logger.info("Disk usage is already below the target. No deletion needed.")
            return

        deleted_items = []
        total_space_freed = 0

        for media in sorted_media:
            current_usage_percent = (used_space / total_space) * 100
            if current_usage_percent <= target_usage:
                logger.info("Disk usage is now below the target. Stopping deletion process.")
                break

            logger.info(f"Processing '{media.title}' for deletion...")

            success = self._delete_media(media, dry_run)

            if success:
                deleted_items.append(media)
                total_space_freed += media.file_size
                used_space -= media.file_size  # Decrement used space locally

                new_usage_percent = (used_space / total_space) * 100
                log_message = (
                    f"Deleted '{media.title}'. Space freed: {media.file_size / 1024**3:.2f} GB. "
                    f"New estimated disk usage: {new_usage_percent:.2f}%."
                )
                if dry_run:
                    log_message = (
                        f"Would delete '{media.title}'. Space to be freed: {media.file_size / 1024**3:.2f} GB. "
                        f"New estimated disk usage: {new_usage_percent:.2f}%."
                    )
                logger.info(log_message)

        self._log_summary(deleted_items, total_space_freed, dry_run)

    def _delete_media(self, media: Media, dry_run: bool) -> bool:
        """
        Deletes a single media item using the appropriate client.
        """
        if dry_run:
            # In dry run, we just log the action and assume success.
            logger.info(f"[DRY RUN] Would delete '{media.title}' (Size: {media.file_size / 1024**3:.2f} GB).")
            return True

        if JELLYSEERR_DELETE_REQUESTS and media.request_id is not None:
            deleted = self.jellyseerr.delete_request(media.request_id)
            if not deleted:
                logger.error(f"Cannot delete request for '{media.title}' with request id '{media.request_id}'.")

        if isinstance(media, Movie) and media.radarr_id:
            return self.radarr.delete_movie(media.radarr_id, delete_files=True)
        elif isinstance(media, TVShow) and media.sonarr_id:
            return self.sonarr.delete_series(media.sonarr_id, delete_files=True)
        else:
            logger.warning(f"Cannot delete '{media.title}': No valid Radarr/Sonarr ID found.")
            return False

    def _log_summary(self, deleted_items: list[Media], total_space_freed: int, dry_run: bool):
        """
        Logs a summary of the deletion process.
        """
        action = "would be" if dry_run else "were"

        if not deleted_items:
            logger.info("No items were deleted.")
            return

        summary_header = "Dry Run Summary" if dry_run else "Deletion Summary"
        logger.info(f"\n--- {summary_header} ---")

        headers = ["Title", "Type", "Size (GB)", "Added Date", "Last Watched"]
        table_data = []
        for item in deleted_items:
            last_watched = item.last_watch_date.date() if item.last_watch_date else "Never"
            table_data.append([
                item.title,
                item.__class__.__name__,
                f"{item.file_size / 1024**3:.2f}",
                item.added_date.date(),
                last_watched
            ])

        logger.info(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}\n")
        logger.info(f"A total of {len(deleted_items)} items {action} deleted.")
        logger.info(f"Total space that {action} freed: {total_space_freed / 1024**3:.2f} GB.")
        logger.info("------------------------" + "-" * len(summary_header))


if __name__ == '__main__':
    # This module is difficult to test standalone without mocking APIs and disk usage.
    # The main CLI will be the primary integration test point.
    logger.info("MediaDeleter service file. Run from main.py for testing.")
