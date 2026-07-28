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
  type    = string
}

variable "postgres_db" {
  type    = string
}

variable "postgres_port" {
  type    = number
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
}