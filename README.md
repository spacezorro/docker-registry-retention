# Docker Registry Retention

This project is inspired by [blixhavn/docker-registry-retention](https://github.com/blixhavn/docker-registry-retention)

I was using /blixhavn/docker-registry-retention and it deleted one of my :latest tags

I started fixing it, and so on and so on and so on until it was a whole new thing.

Here is the new thing...

---

## Overview

The `docker-registry-retention` tool helps manage Docker Registry storage by removing outdated image tags while preserving the most recent ones, including critical tags like `:latest`. It supports both remote and local registries, with built-in garbage collection for local registries to reclaim disk space.

---

## Features

- **Tag Discovery**: Fetches all tags for each image using the Docker Registry API.
- **Creation Date Tracking**: Retrieves tag creation dates from manifest and config data.
- **Persistent Cache**: Stores tag metadata (digests and dates) to minimize redundant API calls.
- **Chronological Sorting**: Orders tags by creation date to safely target older tags for deletion.
- **Protected Tags**: Skips critical tags like `:latest` and handles missing or inaccessible tags gracefully.
- **Configurable Retention**: Deletes all but the `NOF_TAGS_TO_KEEP` newest tags per image, based on digests.
- **Comprehensive Logging**: Records all actions, including successes, failures, and skipped tags, for easy auditing.
- **Local Garbage Collection**: Includes built-in garbage collection for local registries (`mount volume /var/lib/registry`).

> **Important:** Remote Docker Registry must be run with `REGISTRY_STORAGE_DELETE_ENABLED=true` to allow deletion [garbage collection](https://docs.docker.com/registry/garbage-collection/#run-garbage-collection) to actually free storage.

---

## Environment Variables

| Variable              | Description                                                                 | Default                 |
|-----------------------|-----------------------------------------------------------------------------|-------------------------|
| `REGISTRY_URL`        | Base URL of the Docker Registry (e.g., `https://registry.example.com`).     | `http://localhost:5000` |
| `NOF_TAGS_TO_KEEP`    | Number of recent tags to retain per image            .                      | 3                       |
| `DOCKER_USERNAME`     | Username for registry basic auth (optional; skips auth if omitted).         | -                       |
| `DOCKER_PASSWORD`     | Password for registry basic auth (optional).                                | -                       |
| `DRY_RUN`             | If `true`, logs tags that would be deleted without performing deletions.    | `false`                 |

---

## Usage

If you set `REGISTRY_URL` to a remote registry the script deletes tags from it. Garbage collection is not run.

If you volume mount a local registry it starts a local registry server, deletes tags, and runs garbage collection afterward to free up space.

---

## How to Run

### Example (run once on remote registry)
```bash
docker run --rm \
  -e REGISTRY_URL=https://registry.example.com \
  -e DOCKER_USERNAME=admin \
  -e DOCKER_PASSWORD=hunter2 \
  -e NOF_TAGS_TO_KEEP=6 \
  ghcr.io/spacezorro/docker-registry-retention:latest
```

**After running this on a remote repository, run the registry’s garbage collection.**

Don't not do this.

If you delete tags (with this) and don't delete blobs (with garbage collection) what's the point?

---

### Example (run once on local registry) w/ built in garbage collection
```bash
docker run --rm --cpus=0.2 \
  -e NOF_TAGS_TO_KEEP=2 \
  -v /data/my-docker-registry/:/var/lib/registry
  ghcr.io/spacezorro/docker-registry-retention:latest
```

Add a cpu limit because this is fast 🔥🖥️🔥 and ups the load

