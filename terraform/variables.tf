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

# variable "exporters" {
#   type = string
# }