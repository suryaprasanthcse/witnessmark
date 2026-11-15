$ErrorActionPreference = "Stop"

$tag = "witnessmark/minio:RELEASE.2025-09-07T16-13-09Z"
$release = "RELEASE.2025-09-07T16-13-09Z"
$commit = "07c3a429bfed433e49018cb0f78a52145d4bedeb"

docker build --file (Join-Path $PSScriptRoot "Dockerfile.minio") --tag $tag `
    --build-arg "MINIO_TAG=$release" `
    --build-arg "MINIO_COMMIT=$commit" `
    $PSScriptRoot
if ($LASTEXITCODE -ne 0) {
    throw "MinIO source build failed"
}

docker run --rm --entrypoint /usr/local/bin/minio $tag --version
if ($LASTEXITCODE -ne 0) {
    throw "MinIO version verification failed"
}

docker image inspect --format '{{.RepoTags}} {{.Id}} {{json .Config.Labels}}' $tag
