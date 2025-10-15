#!/usr/bin/env python3
import os
import sys
import json
import logging
import pickle
import requests
import random
from collections import defaultdict
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, timezone
UTC = timezone.utc

CACHE_FILE = "/tmp/tag_cache.pkl"
CACHE_EXPIRY_DAYS = 14  # base expiry window
SAVE_INTERVAL = 20  # save cache every N tags processed

# Logging setup
valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Sanity check for log level
if log_level not in valid_log_levels:
    log_level = "INFO"  # Fallback to INFO if invalid
    print(f"Invalid LOG_LEVEL '{log_level}' provided. Defaulting to INFO.")

logging.basicConfig(level=getattr(logging, log_level))
log = logging.getLogger(__name__)

# Environment variables
registry_url = os.getenv("REGISTRY_URL")
username = os.getenv("DOCKER_USERNAME")
password = os.getenv("DOCKER_PASSWORD")
nof_tags_to_keep = int(os.getenv("NOF_TAGS_TO_KEEP", 3))
dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
group_tags = os.getenv("GROUP_TAGS", "true").lower() == "true"

if not registry_url:
    log.error("Registry URL not found. Please set REGISTRY_URL env variable.")
    sys.exit(1)

auth = HTTPBasicAuth(username, password) if (username and password) else None

# ------------------------------------------------------------------------------
# Load and prune tag info cache
# ------------------------------------------------------------------------------
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "rb") as f:
            tag_info_cache = pickle.load(f)
        log.debug(f"Loaded tag info cache with {len(tag_info_cache)} entries")

        now = datetime.now(UTC)
        # wobble so we don't slam the server every expiry days
        expiry_days = CACHE_EXPIRY_DAYS + random.randint(1, 5) 
        cutoff = now - timedelta(days=expiry_days)

        before = len(tag_info_cache)
        tag_info_cache = {
            k: v for k, v in tag_info_cache.items()
            if v.get("cached_at") and datetime.fromisoformat(v["cached_at"]) >= cutoff
        }
        after = len(tag_info_cache)
        log.debug(f"Pruned tag info cache: {before - after} expired, {after} remain")
    except Exception as e:
        log.warning(f"Failed to load tag info cache: {e}")
        tag_info_cache = {}
else:
    tag_info_cache = {}

# ------------------------------------------------------------------------------
# Fetch catalog
# ------------------------------------------------------------------------------
try:
    result = requests.get(f"{registry_url}/v2/_catalog", auth=auth)
    result.raise_for_status()
except requests.RequestException as e:
    log.error(f"Failed to fetch registry catalog: {e}")
    sys.exit(1)

catalog = result.json().get("repositories", [])
stats = {image: 0 for image in catalog}

tags_processed_since_save = 0

# ------------------------------------------------------------------------------
# Process images
# ------------------------------------------------------------------------------
for image in catalog:
    try:
        tags_result = requests.get(f"{registry_url}/v2/{image}/tags/list", auth=auth)
        tags_result.raise_for_status()
        tags = tags_result.json().get("tags") or []
        log.debug(f"Fetched {len(tags)} tags for image {image}")
    except requests.RequestException as e:
        log.error(f"Failed to fetch tags for {image}: {e}")
        continue

    if len(tags) <= nof_tags_to_keep:
        log.info(f"Skipping {image}, it has only {len(tags)} tags")
        continue

    tag_dates = []

    for tag in tags:
        if not group_tags:
            if tag == "latest":
                log.info(f"Skipping {image}:{tag} (latest tag)")
                continue

        key = (image, tag)

        # Cache hit
        if key in tag_info_cache:
            info = tag_info_cache[key]
            if info["created"] is None:
                log.info(f"Skipping {image}:{tag} (previously missing)")
                continue
            created_dt = datetime.fromisoformat(info["created"])
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=UTC)
            digest = info["digest"]
            log.info(f"Cache hit for {image}:{tag}, created {created_dt.isoformat()}")
            tag_dates.append((tag, digest, created_dt))
            continue

        # Fetch manifest
        manifest_url = f"{registry_url}/v2/{image}/manifests/{tag}"
        headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        try:
            r = requests.get(manifest_url, auth=auth, headers=headers)
            if r.status_code == 404:
                log.debug(f"Tag {image}:{tag} listed but missing manifest")
                #tag_info_cache[key] = { "digest": None, "created": None, "cached_at": datetime.now(UTC).isoformat() }
                continue
            r.raise_for_status()
        except requests.RequestException as e:
            log.warning(f"Cannot fetch manifest for {image}:{tag}: {e}")
            #tag_info_cache[key] = { "digest": None, "created": None, "cached_at": datetime.now(UTC).isoformat() }
            continue

        digest = r.headers.get("Docker-Content-Digest")
        if not digest:
            log.warning(f"No digest found for {image}:{tag}")
            continue

        try:
            manifest = r.json()
        except json.JSONDecodeError:
            log.warning(f"Manifest for {image}:{tag} invalid JSON")
            tag_info_cache[key] = { "digest": None, "created": None, "cached_at": datetime.now(UTC).isoformat() }
            continue

        config_digest = manifest.get("config", {}).get("digest")
        if not config_digest:
            log.warning(f"No config digest for {image}:{tag}")
            tag_info_cache[key] = { "digest": None, "created": None, "cached_at": datetime.now(UTC).isoformat() }
            continue

        config_url = f"{registry_url}/v2/{image}/blobs/{config_digest}"
        try:
            config_r = requests.get(config_url, auth=auth)
            config_r.raise_for_status()
            config_data = config_r.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            log.warning(f"Cannot fetch or parse config for {image}:{tag}: {e}")
            continue

        created_str = config_data.get("created")
        if not created_str:
            log.warning(f"No creation date for {image}:{tag}")
            tag_info_cache[key] = { "digest": None, "created": None, "cached_at": datetime.now(UTC).isoformat() }
            continue

        created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        log.info(f"Tag {image}:{tag} created at {created_dt.isoformat()}")

        # Store in cache
        tag_info_cache[key] = {
            "digest": digest,
            "created": created_dt.isoformat(),
            "cached_at": datetime.now(UTC).isoformat()
        }
        tag_dates.append((tag, digest, created_dt))

        # Periodically save cache
        tags_processed_since_save += 1
        if tags_processed_since_save >= SAVE_INTERVAL:
            try:
                with open(CACHE_FILE, "wb") as f:
                    pickle.dump(tag_info_cache, f)
                log.debug(f"Saved tag cache ({len(tag_info_cache)} entries) during run")
            except Exception as e:
                log.warning(f"Failed to save tag cache during run: {e}")
            tags_processed_since_save = 0

    if group_tags:
        # Group tags by creation date
        tag_groups = defaultdict(list)
        for tag, digest, created_dt in tag_dates:
            timestamp = created_dt.replace(second=0,microsecond=0).isoformat()
            tag_groups[timestamp].append((tag, digest, created_dt))

        # Sort groups by timestamp
        sorted_groups = sorted(tag_groups.items(), key=lambda x: datetime.fromisoformat(x[0]), reverse=True)

        # Select tags to keep
        tags_to_keep = []
        tags_to_delete = []
        for i, (timestamp, group_tags) in enumerate(sorted_groups):
            if i < nof_tags_to_keep:
                tags_to_keep.extend(group_tags)
                log.info(f"KEEP   Timestamp: {timestamp}, Tags: {[tag for tag, _, _ in group_tags]}")
            else:
                tags_to_delete.extend(group_tags)
                log.info(f"DELETE Timestamp: {timestamp}, Tags: {[tag for tag, _, _ in group_tags]}")
    else:
        # Sort by creation date
        tag_dates.sort(key=lambda x: x[2])
        tags_to_delete = tag_dates[:-nof_tags_to_keep]
        tags_to_keep = tag_dates[-nof_tags_to_keep:]

    # Dry-run summary
    if dry_run:
        log.info(f"[DRY RUN] Image: {image}")
        log.info("  Tags to keep:")
        for tag, _, created in tags_to_keep:
            log.info(f"    {tag} (created {created.isoformat()})")
        log.info("  Tags to delete:")
        for tag, _, created in tags_to_delete:
            log.info(f"    {tag} (created {created.isoformat()})")
        stats[image] = len(tags_to_delete)
        continue

    # Perform deletion
    for tag, digest, _ in tags_to_delete:
        try:
            delete_result = requests.delete(f"{registry_url}/v2/{image}/manifests/{digest}", auth=auth)
            if delete_result.status_code == 202:
                stats[image] += 1
                log.info(f"Deleted {image}:{tag}")
            else:
                log.error(f"Failed to delete {image}:{tag}, status {delete_result.status_code}")
        except requests.RequestException as e:
            log.error(f"Error deleting {image}:{tag}: {e}")

# ------------------------------------------------------------------------------
# Save final cache
# ------------------------------------------------------------------------------
try:
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(tag_info_cache, f)
    log.debug(f"Saved final tag cache ({len(tag_info_cache)} entries) to {CACHE_FILE}")
except Exception as e:
    log.warning(f"Failed to save final tag cache: {e}")

# ------------------------------------------------------------------------------
# Print out final stats
# ------------------------------------------------------------------------------
print("\nImage cleanup completed. Number of tags deleted:")
print(json.dumps(stats, indent=4))

