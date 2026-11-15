# Run error

The declared run did not complete. No result was inferred.

- Error: `RuntimeError: command failed (1): docker compose -p wm-m4-o1-edge-b2dbaff-minio -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-edge-b2dbaff-minio --config /config --as witnessmark --json
 Volume wm-m4-o1-edge-b2dbaff-minio_omnigraph-root Creating 
 Volume wm-m4-o1-edge-b2dbaff-minio_omnigraph-root Creating 
 Volume wm-m4-o1-edge-b2dbaff-minio_omnigraph-root Created 
 Volume wm-m4-o1-edge-b2dbaff-minio_omnigraph-root Created 
 Container wm-m4-o1-edge-b2dbaff-minio-wm-omnigraph-a-run-8c2f61f127a4 Creating 
 Container wm-m4-o1-edge-b2dbaff-minio-wm-omnigraph-a-run-8c2f61f127a4 Created 
target s3://witnessmark/wm-m4-o1-edge-b2dbaff-minio (inline): direct root s3://witnessmark/wm-m4-o1-edge-b2dbaff-minio; requested=s3://witnessmark/wm-m4-o1-edge-b2dbaff-minio; provider=S3 { region: "us-east-1", endpoint: Some("http://wm-minio:9000"), virtual_hosted_style: false }
Error`
