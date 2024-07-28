# Create a new database
resource "astra_database" "serverless_db" {
  # Required
  name           = "telegram_rag"
  keyspace       = "telegram_rag" # optional, 48 characters max
  cloud_provider = "gcp"
  regions        = ["us-east1"]
  db_type        = "vector"
  # Optional
  deletion_protection = false
  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
  }
}

# --Formatted Outputs--
# astra_database.serverless_db.additional_keyspaces
# astra_database.serverless_db.cqlsh_url
# astra_database.serverless_db.data_endpoint_url
# astra_database.serverless_db.datacenters
# astra_database.serverless_db.grafana_url
# astra_database.serverless_db.graphql_url
# astra_database.serverless_db.node_count
# astra_database.serverless_db.organization_id
# astra_database.serverless_db.owner_id
# astra_database.serverless_db.replication_factor
# astra_database.serverless_db.status
# astra_database.serverless_db.total_storage

output "status" {
  description = "Database status"
  value       = astra_database.serverless_db.status
}

output "cqlsh_url" {
  description = "CQL shell URL"
  value       = astra_database.serverless_db.cqlsh_url
}
