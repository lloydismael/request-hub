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
$tag = "lloydismael12/request-hub:v1.1"
docker build -t $tag -t lloydismael12/request-hub:latest .
docker push $tag
docker push lloydismael12/request-hub:latest
```

> App Service will pull the tagged image directly from Docker Hub. Replace the registry path if you use Azure Container Registry (ACR).

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
  --deployment-container-image-name lloydismael12/request-hub:v1.1
```

If you prefer using ACR:
1. `az acr create ...`
2. Push the image to ACR.
3. Supply `--deployment-container-image-name <acrLoginServer>/request-hub:v1.1` and configure registry credentials via `az webapp config container set`.

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
    WEBSITES_PORT="8000"
```

- `WEBSITES_PORT` tells App Service which port the container listens on (Gunicorn binds to 8000).
- Leave `DJANGO_ALLOWED_HOSTS` empty to rely on the automatic `WEBSITE_HOSTNAME` detection added in `settings.py`. Provide extra hosts if needed (comma-separated).
- If you connect to PostgreSQL, provide `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` values here as well.

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

1. Rebuild and push the Docker image with a new tag (`v1.2`, for example).
2. Point App Service to the new tag:

```powershell
az webapp config container set ^
  --name $APP ^
  --resource-group $RESOURCE_GROUP ^
  --docker-custom-image-name lloydismael12/request-hub:v1.2
az webapp restart --name $APP --resource-group $RESOURCE_GROUP
```

3. Consider enabling continuous deployment via GitHub Actions or Azure Container Registry Webhooks for automated updates.

## Notes on Database Connectivity

- The project defaults to SQLite; for production use Azure Database for PostgreSQL Flexible Server.
- Expose credentials through app settings and ensure outbound access via VNet integration or public firewall rules.
- Run migrations manually if you disable automatic migrations in `entrypoint.sh`.

With these steps, the Dockerized Request Hub application runs on Azure App Service with environment-specific configuration provided through Azure settings.
