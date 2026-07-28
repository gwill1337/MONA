# Configuration guide

## Basic values for configuration in values.yaml
### PCs. for adding list of devices
```yaml
externalPcExporters:
    # - host: "10.0.0.8"
    #   port: 9100
    #   jobName: "pc-test"
```
Other values adding via `terraform.tfvars`

*Just copy the terraform.tfvars.example to terraform.tfvars*

```bash
# use this as an example for terraform.tfvars 

# Telegram alerts
telegram_bot_token     = ""  #<-- telegram token bot for alerts `Optional`
telegram_chat_id       = ""  #<-- telegram chat id for alerts `Optional`
# Username and passowrd for admins and users 
admin_username         = ["admin", "admin2"]  #<-- username for admin/s
admin_password         = ["admin123", "test_123"]  #<-- password for admin/s
user_username          = ["user1"]  #<-- username for user/s
user_password          = ["userpass1"]  #<-- password for user/s

postgres_user          = "myuser"  #<-- DataBase's username 
postgres_db            = "mydb"  #<-- DataBase's name 
postgres_port          = 5432  #<-- DataBase's port

# Passowrd for grafana
grafana_admin_password = "admin123"  #<-- Password for grafana (Username by default 'admin')
```