# Deploying Request Hub to Azure App Service (Linux Container)

This guide walks through running the Dockerized Request Hub Django app on Azure App Service.

## Prerequisites

- Azure subscription with permission to create resource groups and App Service plans
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) 2.55+ installed and signed in (`az login`)
- Docker installed locally (only needed if you plan to build/push images yourself)
- Request Hub image pushed to a registry (Docker Hub is used below)

## 1. Choose or Publish a Container Image

If you have changes locally, rebuild and push the image:

```powershell
# From the project root
$env:DOCKER_BUILDKIT=1
# Inspect existing tags to avoid duplicates
docker images lloydismael12/request-hub --format "{{.Tag}}" | sort
# Update this to the next unused version.
# Patch tags are single digit only: v47.0 through v47.9, then v48.0.
$nextVersion = "v47.1"
$tag = "lloydismael12/request-hub:$nextVersion"
docker build -t $tag -t lloydismael12/request-hub:latest .
docker push $tag
docker push lloydismael12/request-hub:latest
```

> App Service will pull the tagged image directly from Docker Hub. Replace the registry path if you use Azure Container Registry (ACR). Do not create tags such as `v47.10`; after `v47.9`, roll over to `v48.0`.

## 2. Azure Resource Setup

```powershell
$RESOURCE_GROUP = "rg-request-hub"
$PLAN = "plan-request-hub"
$APP = "request-hub-web"
$LOCATION = "southeastasia"  # choose the region closest to your users

az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a Linux App Service plan (SKU B1 = Basic). Adjust size as needed.
az appservice plan create ^
  --name $PLAN ^
  --resource-group $RESOURCE_GROUP ^
  --is-linux ^
  --sku B1

# Create the web app bound to the container image on Docker Hub
az webapp create ^
  --name $APP ^
  --resource-group $RESOURCE_GROUP ^
  --plan $PLAN ^
  --deployment-container-image-name lloydismael12/request-hub:$nextVersion
```

If you prefer using ACR:
1. `az acr create ...`
2. Push the image to ACR.
3. Supply `--deployment-container-image-name <acrLoginServer>/request-hub:$nextVersion` and configure registry credentials via `az webapp config container set`.

## 3. Configure App Settings

Azure passes settings to the container as environment variables. Set the following (adjust values to your environment):

```powershell
az webapp config appsettings set ^
  --name $APP ^
  --resource-group $RESOURCE_GROUP ^
  --settings ^
    DJANGO_SECRET_KEY="$(New-Guid)" ^
    DJANGO_DEBUG="False" ^
    DJANGO_ALLOWED_HOSTS="" ^
    DJANGO_CSRF_TRUSTED_ORIGINS="" ^
    ACS_EMAIL_CONNECTION_STRING="endpoint=https://esgrequesthub.asiapacific.communication.azure.com/;accesskey=<your-access-key>" ^
    ACS_EMAIL_SENDER="DoNotReply@dreadops.site" ^
    WEBSITES_PORT="8000"
```

- `WEBSITES_PORT` tells App Service which port the container listens on (Gunicorn binds to 8000).
- Leave `DJANGO_ALLOWED_HOSTS` empty to rely on the automatic `WEBSITE_HOSTNAME` detection added in `settings.py`. Provide extra hosts if needed (comma-separated).
- If you connect to PostgreSQL, provide `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` values here as well.
- `ACS_EMAIL_CONNECTION_STRING` should point at the Request Hub Azure Communication Services endpoint `https://esgrequesthub.asiapacific.communication.azure.com`.
- `ACS_EMAIL_SENDER` should be the verified sender address `DoNotReply@dreadops.site`.

## 4. Optional: Configure Startup Commands

The container’s `CMD` already runs the entrypoint which collects static files, migrates the database, and starts Gunicorn. No additional App Service startup command is required.

## 5. Restart and Verify

```powershell
az webapp restart --name $APP --resource-group $RESOURCE_GROUP
az webapp browse --name $APP --resource-group $RESOURCE_GROUP
```

The browse command launches the app in your default browser. You can inspect logs via:

```powershell
az webapp log config --name $APP --resource-group $RESOURCE_GROUP --docker-container-logging filesystem
az webapp log tail --name $APP --resource-group $RESOURCE_GROUP
```

## 6. Ongoing Updates

1. Rebuild and push the Docker image with the next tag in sequence (for example, `v47.0` → `v47.1`).
2. Point App Service to the new tag:

```powershell
az webapp config container set ^
  --name $APP ^
  --resource-group $RESOURCE_GROUP ^
  --docker-custom-image-name lloydismael12/request-hub:$nextVersion
az webapp restart --name $APP --resource-group $RESOURCE_GROUP
```

3. Continue incrementing patch versions only up to `.9` for each major/minor cycle; for example, `v47.9` rolls over to `v48.0`. Do not use `v47.10` or higher.
4. Consider enabling continuous deployment via GitHub Actions or Azure Container Registry Webhooks for automated updates.

## Notes on Database Connectivity

- The project defaults to SQLite; for production use Azure Database for PostgreSQL Flexible Server.
- Expose credentials through app settings and ensure outbound access via VNet integration or public firewall rules.
- Run migrations manually if you disable automatic migrations in `entrypoint.sh`.

With these steps, the Dockerized Request Hub application runs on Azure App Service with environment-specific configuration provided through Azure settings.
