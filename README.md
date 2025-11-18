# Reclaimarr

A Python CLI tool to automatically manage disk space by intelligently deleting media from a Jellyfin media stack based on watch history, age, and usage patterns.

## Features

- **Intelligent Deletion:** Prioritizes media for deletion based on watch history (never watched, last watched date).
- **Multi-API Integration:** Fetches data from Jellyfin, Jellystat, Jellyseerr, Radarr, and Sonarr for a holistic view of your media.
- **Disk Space Management:** Automatically deletes media to keep disk usage below a configurable target percentage.
- **Safety First:** Includes a `DRY_RUN` mode to preview deletions without affecting your files.
- **Configurable:** Easily configure API endpoints, keys, and deletion thresholds via a `.env` file.
- **Dockerized:** Comes with a `Dockerfile` and `docker-compose.yml` for easy, containerized deployment.

## Prerequisites

- Python 3.12+
- Docker (for containerized deployment)
- Access to a Jellyfin media stack with the following services:
  - Jellyfin
  - Jellystat
  - Jellyseerr
  - Radarr
  - Sonarr

## Deployment

Reclaimarr is designed to run as a long-running container with a built-in scheduler. The easiest way to deploy it is by adding it to your existing media stack's `docker-compose.yml`.

### Docker Compose Example

Here is a sample `docker-compose.yml` configuration for Reclaimarr. You can add this service to your main compose file.

```yaml
version: '3.8'

services:
  reclaimarr:
    image: ghcr.io/okhr/reclaimarr:latest
    container_name: reclaimarr
    restart: on-failure
    environment:
      # --- Required API Settings ---
      # Assumes you are running Reclaimarr in the same Docker network as your other services.
      - JELLYFIN_URL=http://jellyfin:8096
      - JELLYFIN_API_KEY=${JELLYFIN_API_KEY} # Replace with your actual key or variable
      - JELLYSTAT_URL=http://jellystat:3000
      - JELLYSTAT_API_KEY=${JELLYSTAT_API_KEY}
      - JELLYSEERR_URL=http://jellyseerr:5055
      - JELLYSEERR_API_KEY=${JELLYSEERR_API_KEY}
      - RADARR_URL=http://radarr:7878
      - RADARR_API_KEY=${RADARR_API_KEY}
      - SONARR_URL=http://sonarr:8989
      - SONARR_API_KEY=${SONARR_API_KEY}
      
      # --- Required Path ---
      - MEDIA_PATH=/media

      # --- Optional Settings ---
      - TARGET_USAGE=80
      - MIN_AGE_DAYS=90
      - DRY_RUN=true
      - VERBOSE=false
      - CRON_SCHEDULE="0 3 * * *" # Runs every day at 3 AM. If blank, runs once.
    volumes:
      # Mount your media library. This path must match the one used by your other services.
      # Example: /srv/media on your host machine.
      - /srv/media:/media
```

### Running the Service

The `restart: on-failure` policy is used to ensure the container behaves correctly in both modes:
- **With `CRON_SCHEDULE`:** The container runs continuously as a service. If it ever crashes, Docker will restart it.
- **Without `CRON_SCHEDULE`:** The script runs once and exits cleanly. The `on-failure` policy ensures Docker will **not** restart it, allowing it to act as a one-off task.

To start the service, create a `.env` file for your secrets and run:
```bash
docker-compose up -d
```
The container will start in the background. You can view its logs with `docker-compose logs -f reclaimarr`.

### Important Considerations

#### Network Shares and Snapshots

If your media library is located on a network share (e.g., NFS, SMB) that uses a snapshotting filesystem like ZFS or Btrfs, you may encounter a situation where disk space is not immediately freed after files are deleted. This is because the deleted files are still held by recent snapshots.

If Reclaimarr runs, deletes files, and then runs again before the snapshots containing those files have expired, it will see that the disk usage has not changed and may attempt to delete more content unnecessarily.

**Recommendation:** Configure your `CRON_SCHEDULE` to run at an interval longer than your snapshot retention period. For example, if your snapshots are kept for 24 hours, set the cron schedule to run every 25 hours (`"0 */25 * * *"`) or once a day at a specific time to ensure the snapshots have been cleared.

## Deletion Algorithm

The script prioritizes media for deletion based on the following logic:

1.  **Filter by Age:** Only media older than `MIN_AGE_DAYS` (default: 90) is considered.
2.  **Primary Sort (Never Watched):** Media that has never been watched is prioritized first, sorted by the date it was added (oldest first).
3.  **Secondary Sort (Watched):** Media that has been watched is sorted by the last watched date (oldest first).

The script will delete items from this prioritized list one by one until the disk usage of your media library drops below the `TARGET_USAGE` percentage.

## Configuration

All configuration is handled via the `.env` file. Copy the `.env.example` to `.env` and fill in the values for your environment.

### Required API Settings
```
# Jellyfin
JELLYFIN_URL=http://your-jellyfin-url:8096
JELLYFIN_API_KEY=your-jellyfin-api-key

# Jellystat
JELLYSTAT_URL=http://your-jellystat-url:3791
JELLYSTAT_API_KEY=your-jellystat-api-key

# Jellyseerr
JELLYSEERR_URL=http://your-jellyseerr-url:5055
JELLYSEERR_API_KEY=your-jellyseerr-api-key

# Radarr
RADARR_URL=http://your-radarr-url:7878
RADARR_API_KEY=your-radarr-api-key

# Sonarr
SONARR_URL=http://your-sonarr-url:8989
SONARR_API_KEY=your-sonarr-api-key
```

### Deletion & Scheduler Settings
```
# The target disk usage percentage (e.g., 80 for 80%).
TARGET_USAGE=80
# The minimum age in days before a media item can be deleted.
MIN_AGE_DAYS=90
# The path to your media library inside the Docker container.
MEDIA_PATH=/media
# Set to "true" to run in dry-run mode (no files deleted), or "false" to perform deletions.
DRY_RUN=true
# Set to "true" for verbose logging.
VERBOSE=false
# A cron-style string to schedule runs (e.g., "0 3 * * *"). If blank, runs once.
CRON_SCHEDULE="0 3 * * *"
