# Run error

The declared run did not complete. No result was inferred.

- Error: `RuntimeError: command failed (1): docker compose -p wm-m4-o1-v0-15-0-proxy -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-v0-15-0-proxy --config /config --as witnessmark --json
 Volume wm-m4-o1-v0-15-0-proxy_omnigraph-root Creating 
 Volume wm-m4-o1-v0-15-0-proxy_omnigraph-root Creating 
 Volume wm-m4-o1-v0-15-0-proxy_omnigraph-root Created 
 Volume wm-m4-o1-v0-15-0-proxy_omnigraph-root Created 
 Container wm-m4-o1-v0-15-0-proxy-wm-omnigraph-a-run-7941b7a35437 Creating 
 Container wm-m4-o1-v0-15-0-proxy-wm-omnigraph-a-run-7941b7a35437 Created 
target s3://witnessmark/wm-m4-o1-v0-15-0-proxy (inline): direct root s3://witnessmark/wm-m4-o1-v0-15-0-proxy; requested=s3://witnessmark/wm-m4-o1-v0-15-0-proxy; provider=S3 { region: "us-east-1", endpoint: Some("http://wm-object-proxy:9010"), virtual_hosted_style: false }
Error: 
   0: [91mstorage_root_invalid storage: fail`
