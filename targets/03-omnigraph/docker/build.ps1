param(
    [string]$Scratch = ".state/scratch/omnigraph-build"
)

$ErrorActionPreference = "Stop"
$dockerfile = Join-Path $PSScriptRoot "Dockerfile"
$builds = @(
    @{
        Version = "v0.15.0"
        Tag = "witnessmark/omnigraph:v0.15.0"
        Commit = "373834b4c1c4b29cf0ddd64bee9565f98c60cc26"
        Sha256 = "d7312ce49abca47a6bb47956b6987d32f650fa91678be1abd10e02824937bb15"
        Url = "https://github.com/ModernRelay/omnigraph/releases/download/v0.15.0/omnigraph-linux-x86_64.tar.gz"
    },
    @{
        Version = "edge-20261113-b2dbaff"
        Tag = "witnessmark/omnigraph:edge-b2dbaff"
        Commit = "b2dbaff7584eb849a98fa139876e0ae474e929ea"
        Sha256 = "6b5b449cd4c292eae37ebd8d61a667b293714a5ad573b43a97a2299607297b8d"
        Url = "https://github.com/ModernRelay/omnigraph/releases/download/edge-20261113-b2dbaff/omnigraph-linux-x86_64.tar.gz"
    }
)

foreach ($build in $builds) {
    $context = Join-Path $Scratch $build.Version
    $archive = Join-Path $context "omnigraph-linux-x86_64.tar.gz"
    New-Item -ItemType Directory -Force -Path $context | Out-Null
    if (-not (Test-Path -LiteralPath $archive) -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant() -ne $build.Sha256) {
        curl.exe -fL --retry 3 -o $archive $build.Url
    }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
    if ($actual -ne $build.Sha256) {
        throw "archive checksum mismatch for $($build.Version): $actual"
    }
    docker build --file $dockerfile --tag $build.Tag `
        --build-arg "OMNIGRAPH_VERSION=$($build.Version)" `
        --build-arg "OMNIGRAPH_SOURCE_COMMIT=$($build.Commit)" `
        --build-arg "OMNIGRAPH_ARCHIVE_SHA256=$($build.Sha256)" `
        $context
    if ($LASTEXITCODE -ne 0) {
        throw "docker build failed for $($build.Version)"
    }
}

docker image inspect --format '{{.RepoTags}} {{.Id}} {{json .Config.Labels}}' `
    witnessmark/omnigraph:v0.15.0 witnessmark/omnigraph:edge-b2dbaff
