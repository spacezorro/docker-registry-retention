# Docker Registry Retention

This project is inspired by [blixhavn/docker-registry-retention](https://github.com/blixhavn/docker-registry-retention)

I was using /blixhavn/docker-registry-retention and it deleted one of my :latest tags

I started fixing it, and so on and so on and so on until it was a whole new thing.

Here is the new thing...

---

## Features

* **Fetches the list of tags for each image** in your Docker registry using the registry API.  
* **Retrieves the creation date for each tag** by fetching the manifest and config blob.
* **Maintains a persistent cache** of tag information (digest and creation date) to avoid repeated API calls for tags that have already been processed.  
* **Sorts all tags by creation date**, so older tags can be safely identified and targeted for deletion while keeping the newest tags intact.  
* **Skips important tags**, such as `:latest`, and any tags that are missing or inaccessible.  
* **Deletes all but the `NOF_TAGS_TO_KEEP` most recent tags** by digest, ensuring that only the oldest tags are removed.  
* **Logs all actions and results**, including successes, failures, and any missing or skipped tags, for easier auditing and monitoring.  

> **Important:** Docker Registry must be run with `REGISTRY_STORAGE_DELETE_ENABLED=true` to allow deletion.  
> Must be used in combination with Docker Registry’s [garbage collection](https://docs.docker.com/registry/garbage-collection/#run-garbage-collection) to actually free storage.

---

## Environment Variables

| **Variable** | **Description** | **Default** |
|--------------|-----------------|------------|
| `REGISTRY_URL` | Base URL of the Docker registry (including protocol, e.g., `https://`) | - |
| `NOF_TAGS_TO_KEEP` | Number of tags to retain per image. The most recent tags are always kept. | 3 |
| `DOCKER_USERNAME` | Username for basic auth against the registry. If omitted, auth is skipped. | - |
| `DOCKER_PASSWORD` | Password for basic auth against the registry. | - |
| `DRY_RUN` | If `true`, only prints which tags would be deleted without deleting anything. | `false` |

---

## How to Run

### Example (run once)
```bash
docker run --rm \
  -e REGISTRY_URL=https://registry.example.com \
  -e DOCKER_USERNAME=admin \
  -e DOCKER_PASSWORD=hunter2 \
  -e NOF_TAGS_TO_KEEP=6 \
  ghcr.io/spacezorro/docker-registry-retention:latest
```
---

## IMPORTANT

After tag deletion, manually run the registry’s garbage collection.

Don't not do this.

