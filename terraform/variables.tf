variable "telegram_bot_token" {
  type      = string
  sensitive = true
}

variable "telegram_chat_id" {
  type      = string
  sensitive = true
}

variable "admin_username" {
  type      = list(string)
  sensitive = true
}

variable "admin_password" {
  type      = list(string)
  sensitive = true
}

variable "user_username" {
  type      = list(string)
  sensitive = true
}
variable "user_password" {
  type      = list(string)
  sensitive = true
}

variable "postgres_user" {
  type = string
}

variable "postgres_db" {
  type = string
}

variable "postgres_port" {
  type = number
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
}

variable "LOG_LEVEL_FASTAPI" {
  type = string
}

variable "LOG_LEVEL_CELERY_BEAT" {
  type = string
}

variable "LOG_LEVEL_CELERY_WORKER" {
  type = string
}

variable "postgres_enabled" {
  type = bool
}

variable "external_postgres_url" {
  type = string
}

variable "migration_enabled" {
  type = bool
}

variable "redis_enabled" {
  type = bool
}

variable "external_redis_url" {
  type = string
}

variable "window" {
  type = number
}

variable "min_points" {
  type = number
}

variable "contamination" {
  type = number
}

variable "score_threshold" {
  type = number
}

variable "max_attempts" {
  type = number
}

variable "lockout_seconds" {
  type = number
}

variable "session_ttl" {
  type = number
}

variable "exporters" {
  type    = string
  default = ""
}