$ErrorActionPreference = "Stop"

$tag = "witnessmark/proxy:17ms"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../../..")).Path
docker build --file (Join-Path $PSScriptRoot "Dockerfile.proxy") --tag $tag $root
if ($LASTEXITCODE -ne 0) {
    throw "Delay proxy build failed"
}

docker image inspect --format '{{.Id}}' $tag
exit $LASTEXITCODE
