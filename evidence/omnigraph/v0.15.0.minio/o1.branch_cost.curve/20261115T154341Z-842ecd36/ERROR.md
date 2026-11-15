# Run error

The declared run did not complete. No result was inferred.

- Error: `RuntimeError: command failed (1): docker compose -p wm-m4-o1-v0-15-0-minio -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-v0-15-0-minio --config /config --as witnessmark --json
 Volume wm-m4-o1-v0-15-0-minio_omnigraph-root Creating 
 Volume wm-m4-o1-v0-15-0-minio_omnigraph-root Creating 
 Volume wm-m4-o1-v0-15-0-minio_omnigraph-root Created 
 Volume wm-m4-o1-v0-15-0-minio_omnigraph-root Created 
 Container wm-m4-o1-v0-15-0-minio-wm-omnigraph-a-run-f3c1a6072658 Creating 
 Container wm-m4-o1-v0-15-0-minio-wm-omnigraph-a-run-f3c1a6072658 Created 
target s3://witnessmark/wm-m4-o1-v0-15-0-minio (inline): direct root s3://witnessmark/wm-m4-o1-v0-15-0-minio; requested=s3://witnessmark/wm-m4-o1-v0-15-0-minio; provider=S3 { region: "us-east-1", endpoint: Some("http://wm-minio:9000"), virtual_hosted_style: false }
Error: 
   0: [91mstorage_root_invalid storage: failed to i`
